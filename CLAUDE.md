# Library of Congress MCP Server

A CLI and an MCP server for the JSON API of the Library of Congress: newspapers, books and manuscripts. Each item has a full-text index, and each item resolves to the individual page.

## Stack

- Python ≥3.12, uv, fastMCP ≥2.0.0, httpx ≥0.27.0

## Functions

- **A full-text search at page level** across all of loc.gov, or limited to one collection
- **Filters** for the date range, the language, the US state, the title, the material format, the contributor and the subject heading
- **Keyword-in-context snippets** for any page-level reference, with citation URLs
- **An OCR text download** with a local cache, for one page or for a full item
- **Pagination** at up to 150 results for each request

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

`client.py` holds all the behaviour. `server.py` and `cli.py` are thin presentation layers over it, so the search semantics and the cache stay identical for each method of access. The CLI shows each filter without a condition. The MCP server hides them behind `--enable-advanced-search`.

## API Details

**The dedicated `chroniclingamerica.loc.gov` API does not exist now.** You can reach Chronicling America only as a collection of loc.gov. Thus this client uses the general API, and it treats that collection as one `--collection` value and not as a special case. The default scope is the full site.

Three services, all without a key and without authentication:

| Service | URL | Returns |
|---|---|---|
| Search | `https://www.loc.gov/collections/<slug>/?fo=json` or `/search/?fo=json` | JSON |
| Resource metadata | the same host with `at=resources` | JSON |
| Snippets and OCR | `https://tile.loc.gov/text-services/word-coordinates-service` | JSON |

An item-level reference does not use the third service. Its `fulltext_file` is a direct `.text.txt` URL, served as plain text, that holds the full document.

## Search Parameters

| Parameter | Purpose |
|---|---|
| `q` | the query |
| `fo=json` | **required**; without it the server sends the HTML site |
| `at` | response attributes to include — `results,pagination,search` |
| `c` | results for each page, up to 150 |
| `sp` | 1-based result page number |
| `dl` | display level, `page` or `item` |
| `dates` | `YYYY/YYYY`, the **only** date filter that operates |
| `fa` | facets, joined by `|`, intersecting |
| `sb` | `date` or `date_desc`; omit for relevance |

## Result Ordering

`sort` takes `relevance` (default), `date_asc` or `date_desc`. This is the vocabulary of the client of each other archive. The client expresses relevance when it omits `sb`.

**The totals are true counts, not a relevance tail.** The decade facet counts sum to exactly the reported total (44,089 for `hypnotism`). Thus you can give a total as a count, and an order by date is safe on each query.

## Rate Limiting

A cross-process rate limiter (`ratelimit.py`) paces the requests. The default is **4s**, and `LOC_MIN_REQUEST_INTERVAL` changes it. An in-process semaphore also limits the concurrency.

The Library **publishes** its limit, and the sibling sources do not: **20 requests each minute, with a block of the IP address for one hour after a breach.** Twenty each minute is one request every three seconds exactly. That leaves no margin for clock differences, and no margin for two processes that clear the lock together. Thus the default is four seconds. To lose a quarter of the speed is cheap. To lose an hour in the middle of research is not.

The Library also documents a limit of 10 *bulk* OCR downloads each 10 minutes. That limit governs the collection-level bulk files. It does not govern the per-page text service that this client uses.

## Caching

- **Cache:** the OCR text downloads, and the map from a reference to a transcription location
- **Do not cache:** the search results and the snippets (small, dynamic)
- **Location:** `$XDG_CACHE_HOME/loc-mcp/`, resolved by `paths.cache_dir()`; change it with `--cache-dir` or `LOC_CACHE_DIR`

The segment record under `segments/` is safe to cache, because the map does not change. `search` fills it for each result that it gives, so a search and then a `snippets` or `get` command cost no lookup request.

## Known behaviours and risks

- **The server ignores `start_date` and `end_date`, and gives no message.** They look correct and they appear in third-party examples, but loc.gov accepts only `dates=YYYY/YYYY`. A query that carries them gives the *unfiltered* result set and no error. This is the same class of risk as the date filter of Gallica. Confirmed: `Gedankenleser` with `start_date=1900-01-01&end_date=1901-12-31` gave 359 results that included 1883 and 1946 material. With `dates=1900/1901` it gave 19 results, all inside the range.
- **There is no boolean OR and no NOT.** The server removes `OR`, `NOT`, a `-` at the start, parentheses and `|`. It does not reject them: `hypnotism doctor`, `hypnotism -doctor` and `hypnotism NOT doctor` all report 18,865. Only an implicit AND and `"quoted phrases"` exist. The skill documents this loudly, because it quietly destroys any search written in the idiom of the sibling sources.
- **The `params` argument of `httpx` replaces the query string of a URL. It does not merge into it.** The canonical reference for a newspaper page carries `?sp=N`, which selects the page inside the issue. To pass `params` beside it removed `sp` and resolved every page of an issue to page 1. This gave the OCR of the incorrect page and looked fully healthy: the search result was real, the text was real, but they were not the same page. `_resolve_fulltext_url` now merges the existing query explicitly.
- **`fulltext_file` has two forms, and to assume one form misreports the other.** The division is by *level*, not by material. A **page-level** reference gives a word-coordinates-service URL that carries a `segment=` path, answered as JSON with a `full_text` key. An **item-level** reference gives a direct `.text.txt` URL, answered as plain text. To parse only for `segment=` made each book look like it had no OCR, which is the opposite of the truth: item `05039492` gave 109 KB after a correction. `_fetch_fulltext` branches on the form that came back.
- **Snippets are a page-level capability, not a newspaper capability.** An early version of this client refused books, on the evidence that item `05039492` had no segment. That generalisation was incorrect: a *page* of a book (`gdc.00198495517/?sp=25`) has a segment and gives good keyword-in-context. Thus the refusal in `get_snippets` depends on the absence of a segment, and it speaks about the level and not about the material.
- **The line-end hyphenation has no hyphen to mark it.** The German Fraktur pages use `~`, `—` or `—~`. One sampled page of *Vorwärts* had 94 tildes, 13 em dashes and **zero** plain hyphens. `_clean_ocr_text` joins all of them when a word character follows.
- **The transcription keeps the long ſ, and the index folds it.** `Gedankenleſer` is what the page holds. `Gedankenleser` is what the index matched. Before the fold, a grep for the modern spelling on a page with seven occurrences gave zero. `_clean_ocr_text` folds ſ→s, which is also the standard practice for a transcription of Fraktur. **The client deliberately leaves the snippets unfolded**, because a quotation must read as the page prints it.
- **The HTML pages give HTTP 403, and the JSON API does not.** `www.loc.gov` serves its human site behind an anti-bot wall, so a request for a search page as HTML fails while the same URL with `fo=json` succeeds. Thus a 403 from this client means a block and not a bad query.
- **Truncated bodies and lost connections both occur.** The tests saw an HTTP 200 that carried JSON and stopped in the middle of a string two times, and one transport error, during development. `_get_json` tries one more time after either fault, and then reports honestly. It does not raise a traceback.
- **Use `at=` on each request.** A search of five results gives 1.9 MB without it, and 23 KB with `at=results,pagination,search`, because the unrestricted response carries every facet and the full collection description.
- **Result pages past the end give a clean HTTP 404**, and deep pagination operates to at least result 20,000.
- **An unrecognised facet value gives 0. The server does not remove it.** `original-format:xqzptvw` and a nonsense `contributor:` both come back empty and not unfiltered, so a spelling error in a facet fails loudly. This is worth knowledge, because `start_date` fails in the opposite way, and the two behaviours sit in the same query string.
- **A page-level search matches the item metadata and repeats it across every page.** `Houdini` in `selected-digitized-books` reports 112,647 pages. Its earliest results are pages 1-6 of an 1813 book with no occurrence of the word: the book sits in the Harry Houdini Collection, and the provenance matched. `--level item` reduces the same query to 567. Thus the "totals are true counts" property above holds for the newspapers and **not** for long documents.
- **`subject` is a property of the parent record, so it is a books filter that quietly excludes the newspapers.** The catalogue record carries the headings. For a book that record is the book. For a newspaper page it is the *title*, which gives `magic tricks` on one and `newspapers, united states, charlotte amalie` on the other. `subject:magic tricks` gives 772 pages, all books. Add `original-format:newspaper` and it gives 0 and no error, which is identical to a real absence. `_parse_document` shows `subjects`, so a reader can take the headings from the results and does not guess them. `cli.py` prints them only for material that is not a newspaper, because a dozen inherited place names would hide the result line.
- **`uv tool install --force .` can install an old wheel** when the version did not change. Use `uv tool install --force --reinstall .` after you edit the code.
