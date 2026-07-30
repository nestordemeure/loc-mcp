"""Command-line interface for Library of Congress search.

A thin wrapper over :class:`LocClient` that formats results for reading in a
terminal or by an agent driving the command through a shell. Output is compact
and greppable by default; ``--json`` emits the raw client structures.

Unlike the MCP server, which hides filtering behind an install-time flag, every
filter is available here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx

from .client import (
    DEFAULT_COLLECTION,
    DEFAULT_LEVEL,
    DEFAULT_PER_PAGE,
    DEFAULT_SORT,
    LEVELS,
    MAX_PER_PAGE,
    NEWSPAPER_COLLECTION,
    SORT_ORDERS,
    LocClient,
)
from .paths import cache_dir

PROGRAM_NAME = "locgov"


class PageRange:
    """A 1-indexed, inclusive range of result pages. ``last is None`` means all."""

    def __init__(self, first: int, last: int | None) -> None:
        self.first = first
        self.last = last

    def contains(self, page: int) -> bool:
        return page >= self.first and (self.last is None or page <= self.last)

    def __str__(self) -> str:
        if self.last is None:
            return f"{self.first}-all"
        if self.last == self.first:
            return str(self.first)
        return f"{self.first}-{self.last}"


def parse_page_range(value: str) -> PageRange:
    """Parse a ``--pages`` value: ``3``, ``2-5`` or ``all``."""
    text = value.strip().lower()

    if text == "all":
        return PageRange(1, None)

    try:
        if "-" in text:
            first_text, _, last_text = text.partition("-")
            first, last = int(first_text), int(last_text)
        else:
            first = last = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a page number, a range like 2-5, or 'all'; got {value!r}"
        ) from None

    if first < 1:
        raise argparse.ArgumentTypeError(f"page numbers start at 1; got {value!r}")
    if last < first:
        raise argparse.ArgumentTypeError(f"page range runs backwards: {value!r}")

    return PageRange(first, last)


def format_document(position: int, document: dict[str, Any]) -> str:
    """Render one search result.

    Search resolves to a page, so the reference printed here is directly usable
    by `snippets` and `get` and is also the citation URL a human can open.
    """
    lines = []

    when = document.get("date") or "n.d."
    lines.append(f"[{position}] {when}  {document.get('title') or 'Untitled'}")

    descriptors: list[str] = []
    if newspaper := document.get("newspaper"):
        descriptors.append(str(newspaper))
    if (page_number := document.get("page_number")) is not None:
        descriptors.append(f"p. {page_number}")
    if languages := document.get("languages"):
        descriptors.append(", ".join(languages))
    if states := document.get("states"):
        descriptors.append(", ".join(states))
    if descriptors:
        lines.append(f"    {' · '.join(descriptors)}")

    # Only for non-newspaper material. A newspaper page inherits its title's
    # headings - a dozen place names and the word "newspapers" - which would
    # bury the result line. On a book they are the topical headings, and they
    # are what `--subject` takes, so showing them teaches the filter.
    if not document.get("newspaper") and (subjects := document.get("subjects")):
        lines.append(f"    subjects: {', '.join(subjects[:6])}")

    warnings: list[str] = []
    if document.get("access_restricted"):
        warnings.append("ACCESS RESTRICTED")
    if "online text" not in document.get("online_formats", []):
        warnings.append("no OCR text — cannot be read")
    if warnings:
        lines.append(f"    !! {' · '.join(warnings)}")

    lines.append(f"    {document['reference']}")
    return "\n".join(lines)


async def run_search(args: argparse.Namespace) -> int:
    """Fetch the requested pages, streaming results as each page arrives."""
    client = LocClient(cache_dir=cache_dir(args.cache_dir))
    collected: list[dict[str, Any]] = []
    total_results = 0
    total_pages = 1

    try:
        page = args.pages.first
        while args.pages.contains(page):
            result = await client.search(
                query=args.query,
                page=page,
                per_page=args.per_page,
                collection=args.collection,
                level=args.level,
                from_year=args.from_year,
                to_year=args.to_year,
                language=args.language,
                state=args.state,
                title=args.title,
                original_format=args.format,
                contributor=args.contributor,
                subject=args.subject,
                sort=args.sort,
                readable_only=not args.include_unreadable,
            )

            total_results = result["total_results"]
            total_pages = result["total_pages"]
            documents = result["documents"]

            if page > total_pages:
                break

            if args.json:
                collected.extend(documents)
            else:
                label = args.query or "(filters only)"
                scope = args.collection or "all of loc.gov"
                print(
                    f"# {label} — {total_results} results in {scope}, "
                    f"page {page} of {total_pages}"
                )
                if not documents:
                    print("  (no documents on this page)")
                for offset, document in enumerate(documents):
                    position = (page - 1) * args.per_page + offset + 1
                    print(format_document(position, document))
                print()

            if page >= total_pages:
                break
            page += 1
    finally:
        await client.close()

    if args.json:
        json.dump(
            {
                "query": args.query,
                "total_results": total_results,
                "total_pages": total_pages,
                "pages_fetched": str(args.pages),
                "documents": collected,
            },
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()

    return 0


async def run_snippets(args: argparse.Namespace) -> int:
    """Show a query in context on one page."""
    client = LocClient(cache_dir=cache_dir(args.cache_dir))

    try:
        snippets = await client.get_snippets(reference=args.reference, query=args.query)
    finally:
        await client.close()

    if args.json:
        json.dump(
            {"reference": args.reference, "query": args.query, "snippets": snippets},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 0

    if not snippets:
        print(f"# {args.reference} — no occurrences of {args.query}")
        return 0

    for snippet in snippets:
        terms = ", ".join(snippet.get("matched_terms") or [])
        print(f"# {snippet['reference']}")
        if terms:
            print(f"  matched: {terms}")
        print(f"    {snippet.get('text', '')}")
        if url := snippet.get("url"):
            print(f"        {url}")

    return 0


async def run_get(args: argparse.Namespace) -> int:
    """Download a page's OCR text and print the path to the cached file."""
    client = LocClient(cache_dir=cache_dir(args.cache_dir))

    try:
        path = await client.download_text(reference=args.reference, refresh=args.refresh)
    finally:
        await client.close()

    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description=(
            "Search the Library of Congress: newspapers, books and manuscripts, "
            "all full-text indexed through one API."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="override the download cache location (default: $XDG_CACHE_HOME/loc-mcp)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser(
        "search",
        help="search full text, with optional filters",
        description=(
            "Search the Library of Congress OCR index, across every collection "
            "unless --collection narrows it. Bare words are ANDed and "
            '"quoted phrases" match exactly. There is NO boolean OR and NO NOT: '
            "the words OR and NOT, a leading -, parentheses and | are all silently "
            "stripped, so each variant of a term needs its own search. Results "
            "resolve to individual pages, and the reference printed for each is "
            "both the citation URL and the argument for 'snippets' and 'get'."
        ),
    )
    search.add_argument("query", nargs="?", default="", help="search query (optional if filtering)")
    search.add_argument(
        "--pages",
        type=parse_page_range,
        default=PageRange(1, 1),
        metavar="SPEC",
        help="which result pages to fetch: N, N-M, or 'all' (default: 1)",
    )
    search.add_argument(
        "--per-page",
        type=int,
        default=DEFAULT_PER_PAGE,
        metavar="N",
        help=f"results per request, up to {MAX_PER_PAGE} (default: {DEFAULT_PER_PAGE})",
    )
    search.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        metavar="SLUG",
        help=(
            "narrow to one collection, e.g. "
            f"{NEWSPAPER_COLLECTION} for the newspapers "
            "(default: all of loc.gov)"
        ),
    )
    search.add_argument(
        "--level",
        choices=LEVELS,
        default=DEFAULT_LEVEL,
        help=(
            "resolve hits to an individual page, or to a whole item (default: "
            "page). Snippets and per-page text need page level"
        ),
    )
    search.add_argument("--from-year", type=int, metavar="YEAR", help="earliest year, inclusive")
    search.add_argument("--to-year", type=int, metavar="YEAR", help="latest year, inclusive")
    search.add_argument(
        "--language", metavar="NAME", help="language facet, e.g. german, spanish, swedish"
    )
    search.add_argument(
        "--state", metavar="NAME", help="US state of publication, e.g. wisconsin"
    )
    search.add_argument(
        "--title",
        metavar="TEXT",
        help=(
            "exact newspaper title facet, copied verbatim from a result's "
            "newspaper line, e.g. 'the scranton tribune (scranton, pa.) 1891-1910'"
        ),
    )
    search.add_argument(
        "--format",
        metavar="TYPE",
        dest="format",
        help=(
            "material type, e.g. newspaper, book, periodical, "
            "'manuscript/mixed material'. Books and newspapers behave "
            "differently enough that separating them is often the point"
        ),
    )
    search.add_argument(
        "--contributor",
        metavar="NAME",
        help=(
            "contributor facet, copied verbatim, e.g. "
            "'harry houdini collection (library of congress)'. This is how the "
            "named LoC collections are reached - they are contributors, not "
            "digital collections"
        ),
    )
    search.add_argument(
        "--subject",
        metavar="HEADING",
        help=(
            "subject heading, e.g. 'magic tricks'. Belongs to the parent "
            "catalogue record, so it selects books and returns ZERO "
            "newspapers - do not combine it with a press sweep"
        ),
    )
    search.add_argument(
        "--sort",
        choices=SORT_ORDERS,
        default=DEFAULT_SORT,
        help=(
            "result ordering (default: relevance). loc.gov totals are true match "
            "counts, so date order is safe on any query you intend to sweep"
        ),
    )
    search.add_argument(
        "--include-unreadable",
        action="store_true",
        help=(
            "also return material with no retrievable text. Off by default: a hit "
            "that cannot be read is of no use"
        ),
    )
    search.add_argument("--json", action="store_true", help="emit JSON instead of text")
    search.set_defaults(handler=run_search)

    snippets = subparsers.add_parser(
        "snippets",
        help="show a query in context on one page",
        description=(
            "Show the matched terms on one page in context, with the matches in "
            "{braces} and a citation URL. This is the cheap way to judge a search "
            "result, and often the whole deliverable. Works for any page-level "
            "reference — newspaper, book or manuscript — but not for a whole item."
        ),
    )
    snippets.add_argument("reference", help="page reference, as printed by 'locgov search'")
    snippets.add_argument("query", help="terms to locate within the page")
    snippets.add_argument("--json", action="store_true", help="emit JSON instead of text")
    snippets.set_defaults(handler=run_snippets)

    get = subparsers.add_parser(
        "get",
        help="download a page's OCR text, printing the cache path",
        description=(
            "Download OCR plain text and print the path to the cached file. A "
            "page-level reference yields that one page; an item-level one yields "
            "the whole item in a single file. Line-end hyphenation is rejoined and "
            "long s folded, so the text greps the way the search index matched."
        ),
    )
    get.add_argument("reference", help="page reference, as printed by 'locgov search'")
    get.add_argument(
        "--refresh",
        action="store_true",
        help="re-download even if a cached copy exists",
    )
    get.set_defaults(handler=run_get)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        exit_code = asyncio.run(args.handler(args))
    except KeyboardInterrupt:
        exit_code = 130
    except (RuntimeError, ValueError) as error:
        print(f"{PROGRAM_NAME}: {error}", file=sys.stderr)
        exit_code = 1
    except httpx.HTTPError as error:
        # A dropped connection is not a bug in the query, and a traceback here
        # tells the reader nothing they can act on.
        print(
            f"{PROGRAM_NAME}: network failure talking to loc.gov "
            f"({type(error).__name__}: {error}). Retry once; if it persists, treat "
            "the source as unreachable and say so rather than working around it.",
            file=sys.stderr,
        )
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
