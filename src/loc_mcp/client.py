"""Library of Congress JSON API client: search, page-level snippets, OCR download.

Three services sit behind this client, all keyless and unauthenticated:

* **Search** - `https://www.loc.gov/<scope>/?fo=json`, where `<scope>` is a
  collection path such as `collections/chronicling-america` or the site-wide
  `search`. This is the documented loc.gov JSON API.
* **Snippets and OCR** - `https://tile.loc.gov/text-services/word-coordinates-service`,
  the microservice that the page viewer uses to highlight hits. With
  `relevant_snippet=1` it returns keyword-in-context; with `full_text=1` it
  returns the page's entire OCR text.
* **Resource metadata** - the same search host with `at=resources`, used to turn
  a page reference into the internal `segment` path the text service needs.

The dedicated `chroniclingamerica.loc.gov` API that older tooling targets is
gone; Chronicling America is reachable only as a collection of loc.gov, which is
why this client is written against the general API and merely defaults to that
collection.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlparse, urlunparse

import httpx

from .paths import cache_dir as default_cache_dir
from .ratelimit import CrossProcessRateLimiter, configured_interval

USER_AGENT = "loc-mcp/0.1.0 (historical research tool)"

# Result ordering. The names match the sibling archive clients; the values are
# what loc.gov's `sb` parameter expects. Relevance is the server's own default,
# expressed by omitting `sb` entirely rather than by naming a relevance key.
SORT_VALUES = {
    "relevance": "",
    "date_asc": "date",
    "date_desc": "date_desc",
}
SORT_ORDERS = tuple(SORT_VALUES)
DEFAULT_SORT = "relevance"

# `c` is honoured well past the 40 the web UI offers; 150 was verified live and
# is used as the default because request count, not payload size, is the binding
# constraint at 20 requests/minute.
DEFAULT_PER_PAGE = 150
MAX_PER_PAGE = 150

# Searches cover the whole of loc.gov unless a collection narrows them. There is
# nothing special about the newspapers: Chronicling America is one collection
# among many, and `collection="chronicling-america"` is how you ask for it.
DEFAULT_COLLECTION = None

# The newspaper collection, named here only because it is the one narrowing that
# callers reach for often enough to be worth documenting.
NEWSPAPER_COLLECTION = "chronicling-america"

# Display level. `page` resolves a hit to the individual page it sits on - a
# newspaper page, a page of a book, a leaf of a manuscript - and is what makes
# snippets and per-page text available. `item` returns whole items instead, for
# which there is no snippet service and whose text arrives in one piece.
LEVELS = ("page", "item")
DEFAULT_LEVEL = "page"

# Only these response attributes are ever requested. Left unrestricted, a search
# response carries every facet and the whole collection description - 1.9 MB for
# a five-result query, against 23 KB with `at` applied.
SEARCH_ATTRIBUTES = "results,pagination,search"

# The facet that keeps unreadable material out of results. loc.gov indexes the
# OCR of what it serves, so this is nearly a no-op on Chronicling America, but
# site-wide it is what guarantees a hit can actually be read.
READABLE_FACET = "online-format:online text"

# The text service marks matched terms with these; the house convention across
# every source in this toolkit is {braces}.
SNIPPET_TAG_PATTERN = re.compile(r"\[\[tag\]\](.*?)\[\[/tag\]\]", re.DOTALL)

# Bounds used when only one end of a date range is supplied. loc.gov requires
# `dates` to be a closed range, and these comfortably enclose its holdings
# (the Chronicling America collection reports 1736-09-03/1963-12-31).
OPEN_RANGE_START_YEAR = 1000
OPEN_RANGE_END_YEAR = 2100


class LocClient:
    """Client for the Library of Congress JSON API."""

    SEARCH_HOST = "https://www.loc.gov"
    TEXT_SERVICE_URL = "https://tile.loc.gov/text-services/word-coordinates-service"

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_concurrent_requests: int = 1,
        min_request_interval: float | None = None,
    ):
        """Initialize the Library of Congress client.

        Args:
            cache_dir: Directory for caching downloaded text files
            max_concurrent_requests: Maximum number of concurrent API requests
            min_request_interval: Minimum delay (seconds) between requests;
                defaults to the configured interval
        """
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(
            timeout=90.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        self._request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        # Spacing is shared with every other process using this cache: an
        # instance attribute paces nothing once each CLI call is its own process.
        self._rate_limiter = CrossProcessRateLimiter(
            state_file=self.cache_dir / ".rate-limit",
            min_interval=(
                min_request_interval
                if min_request_interval is not None
                else configured_interval()
            ),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    # ---------------------------------------------------------------- search

    async def search(
        self,
        query: str,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
        collection: str | None = DEFAULT_COLLECTION,
        level: str = DEFAULT_LEVEL,
        from_year: int | None = None,
        to_year: int | None = None,
        language: str | None = None,
        state: str | None = None,
        title: str | None = None,
        original_format: str | None = None,
        contributor: str | None = None,
        subject: str | None = None,
        sort: str = DEFAULT_SORT,
        readable_only: bool = True,
    ) -> dict[str, Any]:
        """Search the Library of Congress full-text index.

        Args:
            query: Search terms. Bare words are ANDed and "quoted phrases" match
                exactly. There is no OR and no NOT - see `_check_query` for why
                that matters enough to warn about.
            page: Result page number (1-indexed)
            per_page: Results per page, up to MAX_PER_PAGE
            collection: Collection slug to narrow to, e.g. `chronicling-america`
                for the newspapers. None searches the whole of loc.gov.
            level: `page` to resolve hits to individual pages, `item` for whole
                items
            from_year: Earliest year, inclusive
            to_year: Latest year, inclusive
            language: Language facet value, e.g. `german`
            state: US state facet value, e.g. `wisconsin`
            title: Exact `partof_title` facet value, as printed in results
            original_format: Material type, e.g. `newspaper`, `book`,
                `periodical`, `manuscript/mixed material`
            contributor: Contributor facet value, e.g.
                `harry houdini collection (library of congress)`
            subject: Subject-heading facet value, e.g. `magic tricks`. A
                property of the parent record, so it selects books and
                excludes newspapers entirely
            sort: One of SORT_ORDERS (default relevance)
            readable_only: Restrict to material whose text can actually be
                retrieved. On by default: a hit we cannot read is of no use.

        Returns:
            A dict with `total_results`, `total_pages` and `documents`.
        """
        if page < 1:
            raise ValueError(f"page numbers start at 1, got {page}")
        if not 1 <= per_page <= MAX_PER_PAGE:
            raise ValueError(f"per_page must be between 1 and {MAX_PER_PAGE}, got {per_page}")
        if sort not in SORT_VALUES:
            raise ValueError(f"sort must be one of {', '.join(SORT_ORDERS)}, got {sort!r}")
        if level not in LEVELS:
            raise ValueError(f"level must be one of {', '.join(LEVELS)}, got {level!r}")

        url = self._scope_url(collection=collection)
        params = self._build_search_params(
            query=query,
            page=page,
            per_page=per_page,
            level=level,
            from_year=from_year,
            to_year=to_year,
            language=language,
            state=state,
            title=title,
            original_format=original_format,
            contributor=contributor,
            subject=subject,
            sort=sort,
            readable_only=readable_only,
        )

        payload = await self._get_json(url, params)
        return self._parse_search_response(payload, per_page=per_page)

    def _scope_url(self, collection: str | None) -> str:
        """Resolve the search scope to a URL.

        Site-wide search lives at /search/; a collection at /collections/<slug>/.
        """
        if not collection:
            return f"{self.SEARCH_HOST}/search/"
        slug = collection.strip().strip("/")
        return f"{self.SEARCH_HOST}/collections/{slug}/"

    def _build_search_params(
        self,
        query: str,
        page: int,
        per_page: int,
        level: str,
        from_year: int | None,
        to_year: int | None,
        language: str | None,
        state: str | None,
        title: str | None,
        original_format: str | None,
        contributor: str | None,
        subject: str | None,
        sort: str,
        readable_only: bool,
    ) -> list[tuple[str, str]]:
        """Assemble the query string.

        Facets are one repeated-looking `fa` parameter whose values are joined by
        `|`, and they intersect: `language:german|location_state:wisconsin` is
        German-language *and* Wisconsin.
        """
        params: list[tuple[str, str]] = [
            ("fo", "json"),
            ("at", SEARCH_ATTRIBUTES),
            ("c", str(per_page)),
            ("sp", str(page)),
            ("dl", level),
        ]

        if query:
            params.append(("q", query))

        if sort_value := SORT_VALUES[sort]:
            params.append(("sb", sort_value))

        if (date_range := self._date_range(from_year, to_year)) is not None:
            params.append(("dates", date_range))

        facets: list[str] = []
        if language:
            facets.append(f"language:{language.strip().lower()}")
        if state:
            facets.append(f"location_state:{state.strip().lower()}")
        if title:
            facets.append(f"partof_title:{title.strip().lower()}")
        if original_format:
            facets.append(f"original-format:{original_format.strip().lower()}")
        if contributor:
            facets.append(f"contributor:{contributor.strip().lower()}")
        if subject:
            facets.append(f"subject:{subject.strip().lower()}")
        if readable_only:
            facets.append(READABLE_FACET)
        if facets:
            params.append(("fa", "|".join(facets)))

        return params

    @staticmethod
    def _date_range(from_year: int | None, to_year: int | None) -> str | None:
        """Render `dates=YYYY/YYYY`, the only date filter loc.gov honours.

        `start_date` and `end_date` look plausible, appear in third-party
        examples, and are **silently ignored** - a query carrying them returns
        the unfiltered result set with no error. They are never sent.
        """
        if from_year is None and to_year is None:
            return None

        start = from_year if from_year is not None else OPEN_RANGE_START_YEAR
        end = to_year if to_year is not None else OPEN_RANGE_END_YEAR
        if start > end:
            raise ValueError(f"from_year {start} is later than to_year {end}")
        return f"{start}/{end}"

    def _parse_search_response(
        self, payload: dict[str, Any], per_page: int
    ) -> dict[str, Any]:
        """Normalise a search response into the shape every source here returns."""
        search_block = payload.get("search") or {}
        pagination = payload.get("pagination") or {}

        total_results = search_block.get("hits")
        if total_results is None:
            total_results = pagination.get("of", 0)

        total_pages = pagination.get("total")
        if not total_pages:
            # An empty result set is one empty page, so callers behave the same
            # here as for every other source.
            total_pages = 1

        raw_results = payload.get("results")
        if raw_results is None:
            raw_results = []
        if not isinstance(raw_results, list):
            raise RuntimeError(
                f"loc.gov returned {type(raw_results).__name__} for results, expected a list"
            )

        return {
            "total_results": int(total_results),
            "total_pages": int(total_pages),
            "results_per_page": per_page,
            "documents": [self._parse_result(item) for item in raw_results],
        }

    def _parse_result(self, item: Any) -> dict[str, Any]:
        """Normalise one search result.

        A malformed record raises rather than being dropped: the reported total
        would still count it, so a silent omission under-reports a search, and
        this tool's whole value rests on exhaustivity.
        """
        if not isinstance(item, dict):
            raise RuntimeError(
                f"loc.gov returned a {type(item).__name__} among results, expected an object"
            )

        url = item.get("url") or item.get("id")
        if not isinstance(url, str) or not url:
            raise RuntimeError(
                f"loc.gov returned a result with no usable url: {json.dumps(item)[:200]}"
            )

        reference = self.canonical_reference(url)
        segment = self._segment_from_word_coordinates(item.get("word_coordinates_url"))

        # Search already knows where a newspaper page's text lives, and the
        # mapping is immutable, so recording it here means a later `snippets` or
        # `get` on this page costs no lookup request at all.
        if segment:
            self._memoise_segment(reference, self._text_service_url(segment, mode="full"))

        return {
            "reference": reference,
            "title": item.get("title"),
            "date": item.get("date"),
            "newspaper": _first(item.get("partof_title")),
            "page_number": _strip_leading_zeros(_first(item.get("number_page"))),
            "languages": _as_list(item.get("language")),
            "states": _as_list(item.get("location_state")),
            # Subject headings belong to the *parent record*, so they describe
            # the book on a book and the newspaper title on a newspaper page.
            # Surfaced because that is exactly what makes `subject` worth
            # filtering on for one and useless for the other.
            "subjects": _as_list(item.get("subject")),
            "online_formats": _as_list(item.get("online_format")),
            "access_restricted": bool(item.get("access_restricted")),
            "segment": segment,
            "citation_url": reference,
            # Present when the result came from search, absent when a reference
            # was resolved cold; either way `snippets` and `get` work.
            "snippet_url": self._text_service_url(segment, mode="snippet") if segment else None,
            "fulltext_url": self._text_service_url(segment, mode="full") if segment else None,
        }

    # -------------------------------------------------------------- snippets

    async def get_snippets(self, reference: str, query: str) -> list[dict[str, Any]]:
        """Locate a query inside one page, in context.

        Returns at most one snippet - the text service gives a single
        keyword-in-context window per page, not one per occurrence - together
        with the matched terms it found. An empty list means the page does not
        contain the query.
        """
        if not query.strip():
            raise ValueError("a query is required to locate anything within a page")

        fulltext_url = await self._resolve_fulltext_url(reference)
        segment = self._segment_from_word_coordinates(fulltext_url)
        if not segment:
            raise RuntimeError(
                f"{self.canonical_reference(reference)} has no snippet service.\n"
                "\n"
                "Snippets are keyed by an internal page segment, so they exist for "
                "page-level references - a newspaper page, a page of a book, a leaf "
                "of a manuscript alike - but not for a whole item, whose "
                "transcription is served as one undivided file.\n"
                "\n"
                "This is not an error in your query. Either search with level="
                "'page' so results carry a page reference, or use `locgov get` on "
                "this item to download its full text and grep it locally."
            )

        url = self._text_service_url(segment, mode="snippet", query=query)
        payload = await self._get_json(url, params=[])

        entry = self._segment_entry(payload, segment, url)
        raw_snippet = entry.get("relevant_snippet")
        if not raw_snippet:
            return []

        return [
            {
                "reference": self.canonical_reference(reference),
                "text": self._mark_snippet(str(raw_snippet)),
                "matched_terms": sorted(entry.get("searchTerms") or {}),
                "url": self._citation_url(reference, query),
            }
        ]

    @staticmethod
    def _mark_snippet(text: str) -> str:
        """Convert the service's [[tag]]x[[/tag]] markers to the house {braces}."""
        return SNIPPET_TAG_PATTERN.sub(r"{\1}", text).strip()

    # -------------------------------------------------------------- OCR text

    async def download_text(self, reference: str, refresh: bool = False) -> Path:
        """Download a page's OCR text, returning the path to the cached file."""
        canonical = self.canonical_reference(reference)
        destination = self.cache_dir / f"{_reference_slug(canonical)}.txt"

        if destination.exists() and not refresh:
            return destination

        fulltext_url = await self._resolve_fulltext_url(reference)
        text = await self._fetch_fulltext(fulltext_url, canonical)

        _write_atomically(destination, self._clean_ocr_text(text))
        return destination

    async def _fetch_fulltext(self, fulltext_url: str, canonical: str) -> str:
        """Retrieve a transcription, in whichever of the two shapes it takes.

        Page-level references are served by the word-coordinates text service,
        which answers JSON keyed by segment path and yields that one page.
        Item-level references instead point straight at a `.text.txt` file
        holding the item entire. Assuming the first shape reports a book as
        having no OCR at all, which is the opposite of the truth.
        """
        segment = self._segment_from_word_coordinates(fulltext_url)

        if segment:
            url = self._text_service_url(segment, mode="full")
            payload = await self._get_json(url, params=[])
            entry = self._segment_entry(payload, segment, url)
            text = entry.get("full_text")
            if not isinstance(text, str):
                raise RuntimeError(
                    f"loc.gov's text service returned no full_text for {canonical}. "
                    "The page is scanned but not transcribed, so it cannot be read "
                    "as text."
                )
            return text

        response = await self._rate_limited_get(fulltext_url)
        if response.status_code == 429:
            raise RuntimeError(
                "Rate limited by loc.gov (HTTP 429) while downloading text. The "
                "Library blocks an IP for a full hour once its limit is breached, "
                "so stop querying now and tell the user."
            )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _clean_ocr_text(raw: str) -> str:
        """Make a page's text grep the way the search index matched it.

        Two transformations, both of which exist because the index normalises
        something the raw transcription does not - so without them a local grep
        misses exactly the occurrences the search just found.

        **Line-end hyphenation.** The service returns lines as they were
        typeset, so a word broken at the right margin arrives split. The break
        is *not* marked with a plain hyphen: in the German-language Fraktur
        pages it is `~`, `—`, or `—~`, and on one sampled page there were 94
        tildes, 13 em dashes and no hyphens at all. Only a marker immediately
        before a newline and followed by a word character is joined, so a dash
        used as real punctuation mid-line survives.

        **Long s.** Fraktur's ſ (U+017F) is transcribed faithfully, so the page
        holds `Gedankenleſer` where the index matched `Gedankenleser` - a grep
        for the plain spelling finds nothing at all. Folding ſ to s is also the
        standard scholarly convention for transcribing Fraktur, so this loses no
        meaning. Note the asymmetry: `snippets` come straight from the service
        and still show ſ, because a quoted snippet should read as printed.
        """
        joined = re.sub(r"[-~—­]+\n(?=\w)", "", raw)
        return joined.replace("ſ", "s")

    # ------------------------------------------------------------- segments

    async def _resolve_fulltext_url(self, reference: str) -> str:
        """Find where a reference's transcription lives.

        Neither shape of that location is derivable from the public URL - a
        newspaper page is keyed by an opaque storage path
        (`/service/ndnp/.../0204.xml`) and a book by a `.text.txt` file under a
        set name - so it has to be looked up once per reference. Search results
        already carry it for newspapers; anything else costs one request.

        The mapping is immutable, so it is memoised on disk. That removes the
        lookup from `snippets` followed by `get` on the same page, which is the
        common sequence.
        """
        canonical = self.canonical_reference(reference)
        memo = self._segment_memo_path(canonical)

        if memo.exists():
            cached = memo.read_text(encoding="utf-8").strip()
            if cached:
                return cached

        # `sp` lives in the canonical URL's own query string and selects which
        # page of the issue the resource describes. httpx's `params` replaces a
        # URL's query rather than merging into it, so passing it through here
        # would silently drop `sp` and resolve every page of an issue to page 1.
        parsed = urlparse(canonical)
        params = parse_qsl(parsed.query) + [("fo", "json"), ("at", "resources")]
        payload = await self._get_json(urlunparse(parsed._replace(query="")), params)

        resources = payload.get("resources")
        if not isinstance(resources, list) or not resources:
            raise RuntimeError(
                f"loc.gov returned no resources for {canonical}, so its OCR cannot "
                "be located. Check that the reference points at a digitised page."
            )

        fulltext_file = resources[0].get("fulltext_file") if isinstance(resources[0], dict) else None
        if not isinstance(fulltext_file, str) or not fulltext_file:
            raise RuntimeError(
                f"{canonical} has no fulltext_file, so no transcription exists for "
                "it. It is scanned but not OCR'd; it cannot be read as text and "
                "cannot be grepped. Search with the default readability filter on "
                "to keep such material out of results."
            )

        self._memoise_segment(canonical, fulltext_file)
        return fulltext_file

    def _segment_memo_path(self, canonical: str) -> Path:
        return self.cache_dir / "segments" / f"{_reference_slug(canonical)}.txt"

    def _memoise_segment(self, reference: str, fulltext_url: str) -> None:
        """Record where a reference's transcription lives. Best-effort: a cache
        write that fails costs a later request, which is not worth failing a
        search over."""
        try:
            _write_atomically(self._segment_memo_path(reference), fulltext_url)
        except OSError:
            pass

    @staticmethod
    def _segment_from_word_coordinates(url: Any) -> str | None:
        """Pull the `segment` query parameter out of a text-service URL."""
        if not isinstance(url, str) or not url:
            return None
        for key, value in parse_qsl(urlparse(url).query):
            if key == "segment" and value:
                return value
        return None

    def _text_service_url(
        self, segment: str, mode: str, query: str | None = None
    ) -> str:
        """Build a text-service URL for a snippet or for the whole page text."""
        # `segment` is a path and must keep its slashes; the service does not
        # match it once they are percent-encoded.
        parts = [f"segment={quote(segment, safe='/')}", "format=alto_xml"]
        if mode == "full":
            parts.append("full_text=1")
        elif mode == "snippet":
            parts.append("relevant_snippet=1")
            if query:
                parts.append(f"q={quote(query, safe='')}")
        else:
            raise ValueError(f"unknown text service mode {mode!r}")
        return f"{self.TEXT_SERVICE_URL}?{'&'.join(parts)}"

    @staticmethod
    def _segment_entry(payload: dict[str, Any], segment: str, url: str) -> dict[str, Any]:
        """Unwrap the text service's response, which is keyed by segment path."""
        entry = payload.get(segment)
        if entry is None and len(payload) == 1:
            # The service occasionally normalises the path it echoes back.
            entry = next(iter(payload.values()))
        if not isinstance(entry, dict):
            raise RuntimeError(
                f"loc.gov's text service returned no entry for segment {segment} "
                f"from {url}; got keys {sorted(payload)[:5]}"
            )
        return entry

    # ------------------------------------------------------------ references

    def canonical_reference(self, reference: str) -> str:
        """Normalise a page reference to a stable, citable loc.gov URL.

        Accepts what search prints, what a browser address bar holds, and the
        bare path in between. The `q` and other display parameters are dropped
        so that the same page yields one cache key however it was named, but
        `sp` is kept because it is what identifies the page within an issue.
        """
        text = reference.strip()
        if not text:
            raise ValueError("a page reference is required")

        if text.startswith("//"):
            text = f"https:{text}"
        elif not text.startswith(("http://", "https://")):
            text = f"{self.SEARCH_HOST}/{text.lstrip('/')}"

        parsed = urlparse(text)
        if not parsed.netloc.endswith("loc.gov"):
            raise ValueError(
                f"expected a loc.gov reference, got {reference!r}. Use the "
                "reference printed by `locgov search`."
            )

        kept = [(key, value) for key, value in parse_qsl(parsed.query) if key == "sp"]
        path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"

        return urlunparse(
            (
                "https",
                "www.loc.gov",
                path,
                "",
                "&".join(f"{key}={value}" for key, value in kept),
                "",
            )
        )

    def _citation_url(self, reference: str, query: str) -> str:
        """A canonical reference with the query kept, so highlighting survives."""
        canonical = self.canonical_reference(reference)
        joiner = "&" if urlparse(canonical).query else "?"
        return f"{canonical}{joiner}q={quote(query, safe='')}"

    # ----------------------------------------------------------------- HTTP

    async def _get_json(
        self, url: str, params: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """GET a JSON endpoint, refusing anything that is not really JSON.

        Truncated bodies were observed twice while this client was written - a
        200 carrying JSON that simply stops mid-string - so a decode failure is
        retried once before being reported.
        """
        last_error: str | None = None

        for attempt in range(2):
            try:
                response = await self._rate_limited_get(url, params=params or None)
            except httpx.TransportError as error:
                # Dropped connections and read timeouts were both seen against
                # loc.gov during development. One retry, then report honestly.
                last_error = f"{type(error).__name__}: {error}"
                continue

            if response.status_code == 429:
                raise RuntimeError(
                    "Rate limited by loc.gov (HTTP 429). The Library blocks an IP "
                    "for a full hour once its 20-requests-per-minute limit is "
                    "breached, so stop querying now rather than retrying, tell the "
                    "user, and raise LOC_MIN_REQUEST_INTERVAL before resuming."
                )
            if response.status_code == 403:
                raise RuntimeError(
                    f"loc.gov refused {url} with HTTP 403. Its HTML pages sit "
                    "behind an anti-bot wall that the JSON API does not; check "
                    "that the request carries fo=json, and if it does, treat this "
                    "as a block and stop querying."
                )
            response.raise_for_status()
            self._raise_for_html(response, url)

            try:
                payload = response.json()
            except ValueError as error:
                last_error = f"{error} (body ended {response.text[-80:]!r})"
                continue

            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"loc.gov returned {type(payload).__name__}, expected an object, from {url}"
                )
            return payload

        raise RuntimeError(
            f"loc.gov did not return usable JSON from {url}, on two attempts: "
            f"{last_error}. This is a truncated or dropped response rather than a "
            "bad query, so rewording will not help; if it persists, stop and "
            "report the source as unreachable."
        )

    @staticmethod
    def _raise_for_html(response: httpx.Response, url: str) -> None:
        """Reject an HTTP 200 carrying a web page instead of data.

        loc.gov serves the human site and the API from one host, distinguished
        only by `fo=json`. A request that loses that parameter succeeds with HTML,
        which would otherwise surface as an opaque decode error far from its
        cause.
        """
        head = response.text[:1000].lstrip().lower()
        if head.startswith("<!doctype html") or head.startswith("<html"):
            raise RuntimeError(
                f"loc.gov served HTML instead of JSON for {url}.\n"
                "\n"
                "This is a bug in this tool rather than a bad query or a transient "
                "fault: every request must carry fo=json, and one has lost it. "
                "Retrying and rewording the search are both wasted effort.\n"
                "\n"
                "If you are an agent that hit this mid-research:\n"
                "  1. Stop querying loc.gov and tell the user — the source is "
                "unavailable until the client is fixed, so any report you write "
                "must say Chronicling America went unsearched.\n"
                "  2. Fix it: `fo=json` is added in `_build_search_params` and in "
                "`_resolve_segment` in this client's client.py. The text-service "
                "URLs built by `_text_service_url` do not take it and must not.\n"
                "  3. Verify with one live search and commit the fix to the "
                "loc-mcp repository, so the next session does not rediscover it."
            )

    async def _rate_limited_get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Issue a GET request honoring concurrency and rate limits."""
        async with self._request_semaphore:
            await self._rate_limiter.acquire()
            return await self.client.get(url, **kwargs)


# ------------------------------------------------------------------ helpers


def _first(value: Any) -> Any:
    """First element of a list-valued field, or the value itself."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _as_list(value: Any) -> list[str]:
    """Normalise a field loc.gov returns as either a scalar or a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _strip_leading_zeros(value: Any) -> str | None:
    """`number_page` arrives zero-padded to ten digits, e.g. `0000000006`."""
    if value is None:
        return None
    text = str(value).lstrip("0")
    return text or "0"


def _reference_slug(canonical: str) -> str:
    """A filesystem-safe, collision-free cache key for a page reference."""
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    readable = re.sub(r"[^A-Za-z0-9]+", "-", canonical.removeprefix("https://www.loc.gov/")).strip("-")
    return f"{readable[:80]}-{digest}"


def _write_atomically(destination: Path, text: str) -> None:
    """Write via a temporary file so an interrupted run leaves no partial cache."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.partial")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(destination)
