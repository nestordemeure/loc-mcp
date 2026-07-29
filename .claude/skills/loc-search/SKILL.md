---
name: loc-search
description: Search the Library of Congress with the `locgov` CLI — American newspapers 1736–1963 in more than a dozen languages, plus digitised books and manuscripts, all page-level full text through one API. Use for the American reception of a performer, the foreign-language immigrant press, and LoC's conjuring literature.
---

# Library of Congress

One keyless API over everything LoC has digitised and transcribed: **newspapers 1736–1963**, **digitised books**, and **manuscript collections**, all full-text indexed and all resolvable to the individual page.

Reach for it for the American side of a career — the touring circuit, local notices, exposure pieces — and as the counterpart to Gallica and ANNO. Two things make it distinctive:

- **It is not only newspapers.** Books and manuscripts sit in the same index and search identically, so the conjuring literature and the personal papers come back alongside the press. Searching them is the default; `--collection` is how you narrow.
- **It is not only English.** The newspaper corpus is deeply multilingual — the American immigrant press published in more languages than most national archives hold.

## Coverage by language

Pages in the newspaper collection, from its own language facet:

| | | | |
|---|---|---|---|
| english 22,499,675 | german 619,712 | spanish 453,914 | polish 169,005 |
| french 135,671 | yiddish 132,713 | italian 88,547 | czech 58,960 |
| norwegian 49,635 | serbian 46,789 | | |

All of it is searchable the same way. A performer touring the United States was covered by whichever community turned out to see them, so the Spanish, Polish and Yiddish press are not a footnote — they are often where a notice survives that the English papers did not run. German is merely the largest of them, and its concentration is useful: 103,779 pages in the 1890s, 128,127 in the 1900s, 177,394 in the 1910s.

## Commands

```sh
locgov search "<query>" [--pages N|N-M|all] [filters] [--json]
locgov snippets <reference> "<query>"   # the query in context on that page
locgov get <reference>                  # OCR text, prints path to the cached file
```

Filters for `search`: `--from-year`, `--to-year`, `--language`, `--state`, `--title`, `--collection`, `--level`, `--per-page`, `--sort`.

`--sort` takes `relevance` (default), `date_asc` or `date_desc`.
`--collection chronicling-america` narrows to the newspapers; omit it to search everything.

A **reference** is the loc.gov URL printed with each result. It is simultaneously the citation link, the argument to `snippets` and `get`, and something a human can paste into a browser to see the scan.

**Search resolves to a page, not a document** — for a book and a manuscript exactly as for a newspaper, so there is no document-to-page step to pay for. A result already says *page 25 of this book*; `snippets` turns it into *and here is the sentence*:

```
$ locgov snippets 'https://www.loc.gov/resource/gdc.00198495517/?sp=25' 'second sight'
# https://www.loc.gov/resource/gdc.00198495517/?sp=25
  matched: second, sight
    ... among others the experiment called “{Second} {Sight}” Now-a-days we can easily
    explain this so-called {Second} {Sight}, which in the ‘40's and '50's attracted the
    attention of the whole civilized world. ...
        https://www.loc.gov/resource/gdc.00198495517/?sp=25&q=second%20sight
```

Matched terms come back in `{braces}`.

## Query syntax — read this before planning a sweep

Bare words are **ANDed**. `"quoted phrases"` match exactly.

**There is no OR. There is no NOT.** This is the defining constraint of this source and it is invisible if you do not know it: `OR`, `NOT`, a leading `-`, parentheses and `|` are all silently **stripped** from the query rather than rejected. Verified:

| Query | Hits |
|---|---|
| `hypnotism` | 44,089 |
| `hypnotism doctor` | 18,865 |
| `hypnotism -doctor` | 18,865 |
| `hypnotism NOT doctor` | 18,865 |

All three of the last rows are the same AND query. A search written as `(Gedankenleser OR Hellseher)` returns pages containing **both** words — a handful instead of hundreds — and reports it as a normal result, so nothing warns you.

**Consequence: one search per variant.** The habit that works on ANNO and DDB, of folding every spelling into a single `(A OR B OR C)`, is actively wrong here and will silently gut a sweep. Budget one request per variant instead, and note that `--per-page 150` makes each one cheap.

**Mind the shell.** `locgov search "Brooklyn Bridge"` is an AND search — the shell eats the quotes. For a phrase you need them to survive: `locgov search '"Brooklyn Bridge"'`. On one 1883 sample that is the difference between 11,098 hits and 2,363.

## The result count is a real count

loc.gov filters rather than ranks, and its totals are honest — the decade facet counts sum to exactly the reported total (44,089 for `hypnotism`). So:

- **A total can be quoted as a count.** "2,363 pages carry the phrase Brooklyn Bridge" is a true statement, unlike the equivalent claim on Gallica.
- **`--sort date_asc` is safe on any query.** There is no relevance tail burying the good material.
- **`--pages all` is meaningful**, subject to cost.

## Being exhaustive

**`--per-page 150`** is the default and the ceiling, so a sweep is far cheaper than on ANNO's fixed 10. 517 results is four requests, not fifty-two.

Narrow before sweeping, with filters that are all verified working:

- `--from-year` / `--to-year` — **note the trap**: the plausible-looking `start_date`/`end_date` parameters that appear in third-party examples are *silently ignored* by loc.gov. This client never sends them; it sends the `dates=YYYY/YYYY` form that works. If you ever hand-build a URL, do the same.
- `--language` takes the facet name in English — `german`, `spanish`, `polish`, `yiddish`, `italian`, `czech`, `french`. It intersects with `--state`.
- `--title` takes the **exact** title string printed on a result's second line, e.g. `'der deutsche correspondent (baltimore, md.) 1841-1918'`. It cut one query from 359 to 105.
- `--collection chronicling-america` to exclude books and manuscripts; `--level item` to get whole documents rather than pages.

Deep paging works to at least result 20,000; loc.gov's own documentation warns of degradation past 100,000.

## Searching in a language other than English

Search in the language of the paper. The index normalises historical orthography, so **search the modern spelling**: `Gedankenleser` matches the printed `Gedankenleſer`, and you should not search for the ſ form.

Vocabulary is the limiting factor more than syntax. For the German press: `Gedankenleser`, `Hellseher`, `Telepath`, `Hypnotiseur`, `Wahrsager`, `Zauberkünstler`, `Gedankenübertragung`. The same care applies to the Spanish, Polish, Italian and Yiddish press — ask for the period term rather than translating a modern one, and note that Yiddish is indexed in Hebrew script.

## False positives and lost hits

**Fraktur's dominant failure is k read as t or d.** Observed on a single 1900 page of *Vorwärts*:

| OCR | Actual |
|---|---|
| `Cytlus` | Cyklus |
| `tönnte` | könnte |
| `duntler` | dunkler |
| `Glocden` | Glocken |
| `Muſithalle` | Musikhalle |
| `tieines` | kleines |
| `Facel` | Fackel |

So **a German term containing `k` is the one most likely to be missed**, including `Zauberkünstler`, `Kartenkunst` and `Okkultismus`. When a German search comes back suspiciously thin, retry with the `k` replaced by `t` before concluding the material is not there. Expect the analogous problem in any language set in a blackletter or unfamiliar face — this pattern was characterised in German because German is the largest such corpus here, not because it is unique to it.

**f and ſ swap**: `ſühlt` for *fühlt*, `Hilſt` for *hilft*.

**Umlauts are sometimes set as a combining e**: `ungläͤubig` for *ungläubig*, which is neither `ä` nor `ae` and defeats both spellings.

**English-language OCR fails more ordinarily** — broken words, dropped punctuation, `rowpond.-d` for *responded* — but the volume of English text is such that noise, not loss, is the usual problem. A phrase search is far more useful than an AND search on common words.

## The cached text is normalised; snippets are not

`locgov get` rewrites two things so the file greps the way the index matched:

- **Line-end hyphenation is rejoined.** The break marker is `~`, `—` or `—~`, *not* a plain hyphen — one sampled page of *Vorwärts* had 94 tildes, 13 em dashes and zero hyphens. So `ſchön~\nſten` becomes `schönsten`.
- **Long ſ is folded to s**, the standard convention for transcribing Fraktur. Before this, `grep Gedankenleser` on a German page returned **nothing** while the page contained seven occurrences.

`snippets` output is **not** normalised — it comes straight from the service and still shows `Gedankenleſer`, because a quoted snippet should read as printed. Quote from snippets; grep the cached file.

## Traps specific to this source

- **Snippets need a page-level reference, not an item.** Any page — newspaper, book or manuscript — has them. A whole item does not, because its transcription is served as one undivided file. `locgov snippets` refuses an item with an explanation and costs no request. Since `--level page` is the default, this only bites if you asked for `--level item`.
- **`get` follows the same split.** A page reference downloads that one page; an item reference downloads the entire document in a single file. Both are one request, so grabbing a whole book is cheap — but check which you asked for before assuming a 1 KB file means a sparse page.
- **Unreadable material is filtered out by default.** `search` restricts to items whose text can actually be retrieved, because a hit that cannot be read is of no use. `--include-unreadable` lifts that, and anything unreadable is then flagged in the output.
- **Its HTML pages are behind an anti-bot wall; the JSON API is not.** A 403 from a normal search means a block, not a bad query — stop rather than retrying.
- **Truncated and dropped responses happen.** The client retries once and then reports honestly; a persistent failure is a real outage, not something to work around.

## Cost

Rate-limited to **one request every four seconds**, single concurrency, shared across processes — parallel subagents share one budget rather than each getting their own. Override with `LOC_MIN_REQUEST_INTERVAL` only with reason.

**The Library publishes its limit and enforces it harshly: 20 requests per minute, and an IP that exceeds it is blocked for a full hour.** That penalty, not politeness, is why the default sits at fifteen a minute. An hour's block mid-research costs far more than the throughput saved.

Budget in requests: `search` is one per result page of up to 150 results; `snippets` and `get` are one each, plus a one-off lookup per reference that is then memoised on disk — and search seeds that memo for every result it returns, so a search followed by snippets costs nothing extra. Downloads are cached under `$XDG_CACHE_HOME/loc-mcp`.

If requests start failing, stop and say so rather than retrying — and record in any report that the source went unsearched.
