# Library of Congress MCP Server

CLI and MCP server for the Library of Congress JSON API: newspapers, books and manuscripts, all full-text indexed and all resolvable to the individual page.

## Stack

- Python ≥3.12, uv, fastMCP ≥2.0.0, httpx ≥0.27.0

## Functionality

- **Page-level full-text search** across the whole of loc.gov, or narrowed to one collection
- **Filters** for date range, language, US state, title, material format, contributor and subject heading
- **Keyword-in-context snippets** for any page-level reference, with citation URLs
- **OCR text download** with local caching, per page or per whole item
- **Pagination** at up to 150 results per request

## Structure

```
loc-mcp/
├── .claude/skills/loc-search/   # Skill documenting the CLI
├── src/loc_mcp/
│   ├── __init__.py
│   ├── client.py           # API client + caching
│   ├── cli.py              # `locgov` command-line interface
│   ├── paths.py            # Cache location resolution
│   ├── ratelimit.py        # Cross-process request pacing
│   ├── server.py           # FastMCP tools
│   └── install.py          # MCP server installer
├── pyproject.toml
└── CLAUDE.md               # This file
```

`client.py` holds all the behaviour; `server.py` and `cli.py` are thin presentation layers over it, so search semantics and caching stay identical no matter how it is called. The CLI exposes every filter unconditionally, where the MCP server hides them behind `--enable-advanced-search`.

## API Details

**The dedicated `chroniclingamerica.loc.gov` API is gone.** Chronicling America is reachable only as a collection of loc.gov, so this client targets the general API and treats that collection as one `--collection` value among others rather than special-casing it. The default scope is the whole site.

Three services, all keyless and unauthenticated:

| Service | URL | Returns |
|---|---|---|
| Search | `https://www.loc.gov/collections/<slug>/?fo=json` or `/search/?fo=json` | JSON |
| Resource metadata | the same host with `at=resources` | JSON |
| Snippets and OCR | `https://tile.loc.gov/text-services/word-coordinates-service` | JSON |

Item-level references bypass the third: their `fulltext_file` is a direct `.text.txt` URL served as plain text, holding the whole document.

## Search Parameters

| Parameter | Purpose |
|---|---|
| `q` | the query |
| `fo=json` | **required**; without it the HTML site is served |
| `at` | response attributes to include — `results,pagination,search` |
| `c` | results per page, up to 150 |
| `sp` | 1-based result page number |
| `dl` | display level, `page` or `item` |
| `dates` | `YYYY/YYYY`, the **only** working date filter |
| `fa` | facets, joined by `|`, intersecting |
| `sb` | `date` or `date_desc`; omit for relevance |

## Result Ordering

`sort` accepts `relevance` (default), `date_asc` or `date_desc`, sharing the vocabulary of the sibling archive clients. Relevance is expressed by omitting `sb`.

**Totals are true counts, not a relevance tail.** The decade facet counts sum to exactly the reported total (44,089 for `hypnotism`), so a total may be quoted as a count and date ordering is safe on any query.

## Rate Limiting

Requests are spaced by a cross-process rate limiter (`ratelimit.py`), default **4s**, overridable with `LOC_MIN_REQUEST_INTERVAL`, on top of an in-process semaphore limiting concurrency.

Unlike the sibling sources, the Library **publishes** its limit: **20 requests per minute, with a one-hour IP block on breach**. Twenty a minute is one per three seconds exactly, leaving no headroom for clock skew or for two processes clearing the lock together, so the default is four seconds. Losing a quarter of the throughput is cheap; losing an hour mid-research is not.

Separately, the Library documents a limit of 10 *bulk* OCR downloads per 10 minutes. That governs the collection-level bulk files, not the per-page text service this client uses.

## Caching

- **Cache:** OCR text downloads, and the reference → transcription-location mapping
- **Don't cache:** Search results and snippets (small, dynamic)
- **Location:** `$XDG_CACHE_HOME/loc-mcp/`, resolved by `paths.cache_dir()`; override with `--cache-dir` or `LOC_CACHE_DIR`

The segment memo under `segments/` is safe to cache because the mapping is immutable. `search` seeds it for every result it returns, so a search followed by `snippets` or `get` costs no lookup request.

## Gotchas

- **`start_date` / `end_date` are silently ignored.** They look plausible and appear in third-party examples, but loc.gov honours only `dates=YYYY/YYYY`. A query carrying them returns the *unfiltered* result set with no error — the same class of trap as Gallica's date filter. Verified: `Gedankenleser` with `start_date=1900-01-01&end_date=1901-12-31` returned 359 hits including 1883 and 1946 material; with `dates=1900/1901` it returned 19, all in range.
- **There is no boolean OR and no NOT.** `OR`, `NOT`, a leading `-`, parentheses and `|` are stripped rather than rejected: `hypnotism doctor`, `hypnotism -doctor` and `hypnotism NOT doctor` all report 18,865. Only implicit AND and `"quoted phrases"` exist. This is documented loudly in the skill because it silently guts any sweep written in the sibling sources' idiom.
- **`httpx`'s `params` replaces a URL's query string rather than merging into it.** The canonical reference for a newspaper page carries `?sp=N`, which selects the page within the issue; passing `params` alongside it dropped `sp` and resolved every page of an issue to page 1. This produced OCR for the wrong page while looking entirely healthy — the search result was real, the text was real, they just were not the same page. `_resolve_fulltext_url` now merges the existing query explicitly.
- **`fulltext_file` has two shapes and assuming one misreports the other.** The split is by *level*, not by material: a **page-level** reference gives a word-coordinates-service URL carrying a `segment=` path, answered as JSON with a `full_text` key, while an **item-level** one gives a direct `.text.txt` URL answered as plain text. Parsing only for `segment=` made every book look like it had no OCR at all, which is the opposite of the truth — item `05039492` returned 109 KB once handled. `_fetch_fulltext` branches on which shape came back.
- **Snippets are a page-level capability, not a newspaper one.** An early version of this client refused books outright, on the evidence that item `05039492` had no segment. That was the wrong generalisation: a *page* of a book (`gdc.00198495517/?sp=25`) has a segment and returns perfectly good keyword-in-context. The refusal in `get_snippets` is therefore keyed on the absence of a segment, and says so in terms of level rather than material.
- **Line-end hyphenation is not marked with a hyphen.** The German Fraktur pages use `~`, `—` or `—~`; one sampled page of *Vorwärts* had 94 tildes, 13 em dashes and **zero** plain hyphens. `_clean_ocr_text` joins all of them when followed by a word character.
- **The transcription keeps long ſ but the index folds it.** `Gedankenleſer` is what the page holds; `Gedankenleser` is what the index matched. Before folding, a grep for the modern spelling on a page containing seven occurrences returned zero. `_clean_ocr_text` folds ſ→s, which is also standard practice for transcribing Fraktur. **Snippets are deliberately left unfolded**, since a quoted snippet should read as printed.
- **HTML pages 403; the JSON API does not.** `www.loc.gov` serves its human site behind an anti-bot wall, so fetching a search page as HTML fails while the same URL with `fo=json` succeeds. A 403 from this client therefore means a block rather than a bad query.
- **Truncated bodies and dropped connections both occur.** A 200 carrying JSON that stops mid-string was seen twice, and a transport error once, during development. `_get_json` retries once on either and then reports honestly rather than raising a traceback.
- **`at=` is worth using on every request.** A five-result search returns 1.9 MB unrestricted and 23 KB with `at=results,pagination,search`, because the unrestricted response carries every facet and the whole collection description.
- **Result pages past the end are a clean 404**, and deep paging works to at least result 20,000.
- **An unrecognised facet value returns 0 rather than being dropped.** `original-format:xqzptvw` and a nonsense `contributor:` both come back empty rather than unfiltered, so facet typos fail loudly. Worth knowing because `start_date` fails the other way, and the two behaviours sit in the same query string.
- **A page-level search matches item metadata and fans it out over every page.** `Houdini` in `selected-digitized-books` reports 112,647 pages, whose earliest results are pages 1-6 of an 1813 book with no occurrence of the word - it sits in the Harry Houdini Collection, and the provenance matched. `--level item` collapses the same query to 567. So the "totals are true counts" property above holds for newspapers and **not** for long-form material.
- **`subject` is a parent-record property, so it is a books filter that silently excludes newspapers.** Headings are assigned to the catalogue record, which for a book is the book and for a newspaper page is the *title* - hence `magic tricks` on one and `newspapers, united states, charlotte amalie` on the other. `subject:magic tricks` returns 772 pages, all books; add `original-format:newspaper` and it returns 0 rather than erroring, which is indistinguishable from real absence. `_parse_document` surfaces `subjects` so the headings can be read off results rather than guessed, and `cli.py` prints them only for non-newspaper material because a newspaper's dozen inherited place names would bury the result line.
- **`uv tool install --force .` can install a stale wheel** when the version has not changed. Use `uv tool install --force --reinstall .` after editing.
