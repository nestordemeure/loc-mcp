---
name: loc-search
description: Search Chronicling America and the wider Library of Congress with the `locgov` CLI. Use for the American press 1736–1963 — including a large German-language immigrant press — and for LoC's digitised books on conjuring and allied subjects.
---

# Chronicling America / Library of Congress

The Library of Congress's historic newspaper collection: American papers from **1736 to 1963**, page-level full text, free and keyless. The same CLI reaches the rest of loc.gov, where digitised **books** are full-text indexed too.

Reach for it for the American reception of a performer — the touring circuit, the local notices, the exposure pieces — and as the counterpart to Gallica and ANNO. Two things make it unusually valuable here:

- **619,712 German-language pages**, concentrated exactly where they are wanted: 103,779 in the 1890s, 128,127 in the 1900s, 177,394 in the 1910s. This is the German-American immigrant press — *Der Deutsche Correspondent* (Baltimore), *Vorwärts* (Milwaukee), *Der Nordstern* (Minnesota), the *Washington Journal* — reporting the same performers the Berlin and Vienna papers did, often reprinting them.
- **Digitised books** via `--all-loc`, which is where the conjuring literature lives.

## Commands

```sh
locgov search "<query>" [--pages N|N-M|all] [filters] [--json]
locgov snippets <reference> "<query>"   # the query in context on that page
locgov get <reference>                  # OCR text, prints path to the cached file
```

Filters for `search`: `--from-year`, `--to-year`, `--language`, `--state`, `--title`, `--collection`, `--all-loc`, `--level`, `--per-page`, `--sort`.

`--sort` takes `relevance` (default), `date_asc` or `date_desc`.

A **reference** is the loc.gov URL printed with each result. It is simultaneously the citation link, the argument to `snippets` and `get`, and something a human can paste into a browser to see the scan.

**Search resolves to a page, not an issue** — unlike ANNO, there is no issue-to-page step to pay for. A result already says *page 3 of this issue*; `snippets` turns it into *and here is the sentence*:

```
$ locgov snippets 'https://www.loc.gov/resource/sn83045812/1900-09-30/ed-1/?sp=3' 'Gedankenleser'
# https://www.loc.gov/resource/sn83045812/1900-09-30/ed-1/?sp=3
  matched: gedankenleſer
    ... es hören. Ich bin der {Gedankenleſer} Speeles, und eröffne morgen hier einen
    Cytlus von Vorſtellungen. ...
        https://www.loc.gov/resource/sn83045812/1900-09-30/ed-1/?sp=3&q=Gedankenleser
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

- **A total can be quoted as a count.** "2,363 pages in Chronicling America carry the phrase Brooklyn Bridge" is a true statement, unlike the equivalent claim on Gallica.
- **`--sort date_asc` is safe on any query.** There is no relevance tail burying the good material.
- **`--pages all` is meaningful**, subject to cost.

## Being exhaustive

**`--per-page 150`** is the default and the ceiling, so a sweep is far cheaper than on ANNO's fixed 10. 517 results is four requests, not fifty-two.

Narrow before sweeping, with filters that are all verified working:

- `--from-year` / `--to-year` — **note the trap**: the plausible-looking `start_date`/`end_date` parameters that appear in third-party examples are *silently ignored* by loc.gov. This client never sends them; it sends the `dates=YYYY/YYYY` form that works. If you ever hand-build a URL, do the same.
- `--language german` cuts `Hellseher` from 517 to the German subset; `--state wisconsin` narrows further, and the two intersect.
- `--title` takes the **exact** title string printed on a result's second line, e.g. `'der deutsche correspondent (baltimore, md.) 1841-1918'`. It cut `Gedankenleser` from 359 to 105.

Deep paging works to at least result 20,000; loc.gov's own documentation warns of degradation past 100,000.

## Searching in German

The German-language press is a large fraction of the value here, and it is Fraktur. Search in German: `Gedankenleser`, `Hellseher`, `Telepath`, `Hypnotiseur`, `Wahrsager`, `Zauberkünstler`, `Gedankenübertragung`.

**The index folds long ſ to s, so search the modern spelling.** `Gedankenleser` matches the printed `Gedankenleſer`. Do not search for the ſ form.

## False positives and lost hits

**The dominant Fraktur failure is k read as t or d.** Observed on a single 1900 page of *Vorwärts*:

| OCR | Actual |
|---|---|
| `Cytlus` | Cyklus |
| `tönnte` | könnte |
| `duntler` | dunkler |
| `Glocden` | Glocken |
| `Muſithalle` | Musikhalle |
| `tieines` | kleines |
| `Facel` | Fackel |

So **a German term containing `k` is the one most likely to be missed**, and that includes `Zauberkünstler`, `Kartenkunst` and `Okkultismus`. When a German search comes back suspiciously thin, retry with the `k` replaced by `t` (`Cytlus`, `Zaubertünſtler`) before concluding the material is not there.

**f and ſ swap**: `ſühlt` for *fühlt*, `Hilſt` for *hilft*.

**Umlauts are sometimes set as a combining e**: `ungläͤubig` for *ungläubig*, which is neither `ä` nor `ae` and defeats both spellings.

**English-language OCR fails more ordinarily** — broken words, dropped punctuation, `rowpond.-d` for *responded* — but the volume of English text is such that noise, not loss, is the usual problem. Expect a phrase search to be far more useful than an AND search on common words.

## The cached text is normalised; snippets are not

`locgov get` rewrites two things so the file greps the way the index matched:

- **Line-end hyphenation is rejoined.** The break marker is `~`, `—` or `—~`, *not* a plain hyphen — one sampled page had 94 tildes, 13 em dashes and zero hyphens. So `ſchön~\nſten` becomes `schönsten`.
- **Long ſ is folded to s**, the standard convention for transcribing Fraktur. Before this, `grep Gedankenleser` on a German page returned **nothing** while the page contained seven occurrences.

`snippets` output is **not** normalised — it comes straight from the service and still shows `Gedankenleſer`, because a quoted snippet should read as printed. Quote from snippets; grep the cached file.

## Traps specific to this source

- **Books have no snippet service.** `--all-loc` reaches digitised books, and they carry full text, but the keyword-in-context endpoint is newspaper-only. `locgov snippets` refuses them with an explanation and costs no request. Use `locgov get` and grep locally — a book's whole transcription arrives as one file, so this is one request rather than one per page.
- **`get` on a newspaper is one page; `get` on a book is the whole book.** The two shapes of transcription are different services, and the client handles both, but budget accordingly.
- **Unreadable material is filtered out by default.** `search` restricts to items whose text can actually be retrieved, because a hit that cannot be read is of no use. `--include-unreadable` lifts that, and anything unreadable is then flagged in the output.
- **Its HTML pages are behind an anti-bot wall; the JSON API is not.** A 403 from a normal search means a block, not a bad query — stop rather than retrying.
- **Truncated and dropped responses happen.** The client retries once and then reports honestly; a persistent failure is a real outage, not something to work around.

## Cost

Rate-limited to **one request every four seconds**, single concurrency, shared across processes — parallel subagents share one budget rather than each getting their own. Override with `LOC_MIN_REQUEST_INTERVAL` only with reason.

**The Library publishes its limit and enforces it harshly: 20 requests per minute, and an IP that exceeds it is blocked for a full hour.** That penalty, not politeness, is why the default sits at fifteen a minute. An hour's block mid-research costs far more than the throughput saved.

Budget in requests: `search` is one per result page of up to 150 results; `snippets` and `get` are one each, plus a one-off lookup per reference that is then memoised on disk — and search seeds that memo for every result it returns, so a search followed by snippets costs nothing extra. Downloads are cached under `$XDG_CACHE_HOME/loc-mcp`.

If requests start failing, stop and say so rather than retrying — and record in any report that the source went unsearched.
