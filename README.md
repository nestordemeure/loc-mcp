# loc-mcp

A CLI and MCP server for the **Library of Congress JSON API**: newspapers, books
and manuscripts, all full-text indexed and all resolvable to the individual page.

Keyless, no registration, no affiliation required.

## Scope

Searches cover the whole of loc.gov by default. `--collection <slug>` narrows to
one collection — `chronicling-america` for the historic newspapers, which is
where the bulk of the transcribed text lives.

There is nothing special-cased about the newspapers. The dedicated
`chroniclingamerica.loc.gov` API has been retired and that collection is now
reachable only as one collection of loc.gov, so it is simply one value of
`--collection` like any other.

## Install

```sh
uv tool install .
```

## Commands

```sh
locgov search "<query>" [--pages N|N-M|all] [filters] [--json]
locgov snippets <reference> "<query>"   # the query in context on that page
locgov get <reference>                  # OCR text, prints path to the cached file
```

A **reference** is the loc.gov URL printed for each search result. It is both the
citation link and the argument the other two commands take.

```
$ locgov search '"Brooklyn Bridge"' --collection chronicling-america \
    --from-year 1883 --to-year 1883 --per-page 2
# "Brooklyn Bridge" — 2363 results in chronicling-america, page 1 of 1182
[1] 1883-06-16  Image 2 of The Lincoln County leader (White Oaks, Lincoln County, N.M.), June 16, 1883
    the lincoln county leader (white oaks, lincoln county, n.m.) 1882-189? · p. 2 · english · new mexico
    https://www.loc.gov/resource/sn87090072/1883-06-16/ed-1/?sp=2
```

Note the nested quotes. `'"Brooklyn Bridge"'` is a phrase search; `"Brooklyn Bridge"`
lets the shell strip the quotes and becomes an AND search, which on this same
1883 range reports 11,098 hits instead of 2,363.

Filters for `search`: `--from-year`, `--to-year`, `--language`, `--state`,
`--title`, `--collection`, `--level`, `--per-page`, `--sort`.

`--sort` takes `relevance` (default), `date_asc` or `date_desc`.

## Query syntax

Bare words are **ANDed**, and `"quoted phrases"` match exactly.

**There is no boolean OR and no NOT.** The words `OR` and `NOT`, a leading `-`,
parentheses and `|` are all silently stripped from the query rather than
rejected:

| Query | Hits |
|---|---|
| `telegraph` | 3,212,711 |
| `telegraph cable` | 594,470 |
| `telegraph -cable` | 594,470 |
| `telegraph NOT cable` | 594,470 |

The last three are the same AND query. Each variant of a term therefore needs its
own search, and a query written as `(a OR b)` quietly returns only pages holding
*both*. This is the single most important thing to know before planning a sweep
against this source.

## Result totals are true counts

Unlike a relevance-ranked archive, loc.gov filters: the reported total is a real
count of matching pages, so it can be quoted as one and `--sort date_asc` is safe
on any query. The decade facet counts sum exactly to the reported total.

## Pages, not documents

`--level page` is the default and resolves a hit to the individual page it sits
on, for a book or a manuscript exactly as for a newspaper. That is what makes
`snippets` and per-page text available. `--level item` returns whole documents
instead; those have no snippet service, and `get` on one downloads the entire
transcription in a single file.

## Readability

By default `search` returns only material whose text can actually be retrieved
(`online-format:online text`). A hit that cannot be read is of no use, so this is
on unless you pass `--include-unreadable`, and anything unreadable that does slip
through is flagged in the output.

## Cost

Requests are paced at **one every four seconds**, shared across processes, so
parallel callers share one budget. The Library publishes a limit of **20 requests
per minute and blocks an offending IP for a full hour**, which is what the
conservative default is for. Override with `LOC_MIN_REQUEST_INTERVAL` only with
reason.

Budget in requests: `search` is one request per result page (up to 150 results
each), `snippets` and `get` are one request each after a one-off lookup per page
that is then memoised on disk — and `search` seeds that memo for every result it
returns. OCR downloads are cached under `$XDG_CACHE_HOME/loc-mcp`.

## MCP server

```sh
uv run loc-mcp-install
```

Installs to Claude Code, Codex CLI and Gemini CLI. The CLI is the primary
interface; the server exposes the same client.

## License

Apache 2.0
