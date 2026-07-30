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

All of it is searchable the same way. A performer touring the United States was covered by whichever community turned out to see them, so the Spanish, Polish and Yiddish press are not a footnote — they are often where a notice survives that the English papers did not run.

**The decade shape differs sharply by language, and it decides whether a subset is worth searching at all.** Each column sums to that language's total exactly, so these are counts rather than estimates:

| Decade | german | spanish | polish | yiddish | italian |
|---|---|---|---|---|---|
| 1880s | | 22,933 | 1,642 | 1 | — |
| 1890s | 103,779 | 44,278 | 22,010 | 296 | 3,974 |
| 1900s | 128,127 | 63,073 | 39,083 | **0** | 24,033 |
| 1910s | 177,394 | 66,021 | 70,108 | 24,719 | 34,400 |
| 1920s | 24,075 | 70,765 | 31,847 | 24,178 | 6,705 |

Read the holes as facts about the collection, not about your query. **The Yiddish subset has no 1900s at all** — a Yiddish search bounded to that decade returns zero, and that is coverage, not OCR and not a mistake. Yiddish begins in earnest in 1910 and peaks in the 1940s (46,873). Polish collapses after 1929 and stops entirely by 1949. Italian peaks in the 1910s and thins to 6,705 in the 1920s. Only Spanish is thick right across 1880–1930, and it alone continues in volume past 1930.

## Commands

```sh
locgov search "<query>" [--pages N|N-M|all] [filters] [--json]
locgov snippets <reference> "<query>"   # the query in context on that page
locgov get <reference>                  # OCR text, prints path to the cached file
```

Filters for `search`: `--from-year`, `--to-year`, `--language`, `--state`, `--title`, `--format`, `--contributor`, `--subject`, `--collection`, `--level`, `--per-page`, `--sort`.

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

**This holds for the newspapers. It does not hold for books**, where a page-level total counts metadata matches fanned out across every page of an item — `Houdini` reports 112,647 pages of digitised books and 567 actual items. See **Books, periodicals and manuscripts** below before quoting any total that includes long-form material.

## Being exhaustive

**`--per-page 150`** is the default and the ceiling, so a sweep is far cheaper than on ANNO's fixed 10. 517 results is four requests, not fifty-two.

Narrow before sweeping, with filters that are all verified working:

- `--from-year` / `--to-year` — **note the trap**: the plausible-looking `start_date`/`end_date` parameters that appear in third-party examples are *silently ignored* by loc.gov. This client never sends them; it sends the `dates=YYYY/YYYY` form that works. If you ever hand-build a URL, do the same.
- `--language` takes the facet name in English — `german`, `spanish`, `polish`, `yiddish`, `italian`, `czech`, `french`. It intersects with `--state`.
- `--title` takes the **exact** title string printed on a result's second line, e.g. `'der deutsche correspondent (baltimore, md.) 1841-1918'`. It cut one query from 359 to 105.
- `--format` takes the material type — `newspaper`, `book`, `periodical`, `manuscript/mixed material`. Separating books from newspapers matters more here than it sounds; see below.
- `--contributor` takes a contributor facet verbatim, which is how LoC's named collections are reached.
- `--subject` takes a Library of Congress subject heading — **books only, see below**.
- `--collection chronicling-america` to exclude books and manuscripts; `--level item` to get whole documents rather than pages.

**A misspelled facet value returns 0, not the unfiltered set.** `--format xqzptvw` and `--contributor 'not a real contributor'` both return zero rather than quietly dropping the filter, so a facet typo fails loudly. This is the opposite of the `start_date` trap, and it means a surprising 0 is worth double-checking against the bare facet before you believe it.

Deep paging works to at least result 20,000; loc.gov's own documentation warns of degradation past 100,000.

## Books, periodicals and manuscripts

They are searched by default, and for this field they are not the minor half of the source. Page counts via `--format`:

| Term | total | newspaper | book | periodical | manuscript |
|---|---|---|---|---|---|
| `spiritualism` | 203,917 | 66,107 | 136,891 | 595 | 323 |
| `conjuring` | 137,554 | 93,865 | 41,145 | 1,980 | 547 |
| `mesmerism` | 30,803 | 18,456 | 12,075 | 192 | 80 |
| `clairvoyance` | 26,578 | 12,466 | 11,211 | 197 | 2,704 |
| `"second sight"` | 22,747 | 18,513 | 4,038 | 164 | 30 |
| `legerdemain` | 19,487 | 15,778 | 3,486 | 170 | 53 |
| `prestidigitation` | 2,611 | 1,517 | 1,048 | 42 | 3 |
| `"Robert-Houdin"` | 2,425 | 720 | 1,681 | 24 | 0 |

`"Robert-Houdin"` is more than twice as strong in books as in the press, and `prestidigitation` runs 778 French pages against 1,817 English. **The Library holds the conjuring literature itself, in French as well as English** — Ponsin's *Nouvelle magie blanche dévoilée* (1853) and Robert-Houdin's *Confidences et révélations* (1868) are both there in full text.

**`--collection selected-digitized-books` is the narrowing to reach for**, and it covers bound periodical runs as well as books: `prestidigitation` returns 1,070 pages there.

**The two conjuring collections are not collections — they are contributors.** LoC's *Harry Houdini Collection* and *McManus-Young Collection* supply much of this material, 718 and 672 pages respectively of the 2,611 for `prestidigitation`, but there is no `/collections/harry-houdini-collection/` to narrow to. Reach them with `--contributor`:

```sh
locgov search 'prestidigitation' --contributor 'harry houdini collection (library of congress)'
```

The value must be verbatim, lowercase, parenthetical suffix included. That query returns 718 pages — Houdini's own library, which is as close to a curated conjuring collection as this source has.

### The metadata trap — read this before quoting any book count

**On long-form material a page-level search matches the item's *metadata* as well as its text, then reports that single match once per page.** This is the defining hazard here and it is invisible in the output.

Verified: `Houdini` inside `selected-digitized-books` reports **112,647 pages**. Sorted `date_asc`, the first six results are pages 1 to 6 of *An essay towards a theory of apparitions*, published in **1813** — sixty-one years before Houdini was born. `snippets` on page 3 answers *no occurrences of Houdini*. The book sits in the Harry Houdini Collection, and one provenance match became a hit on every page of it.

So for books, unlike newspapers, **a total counts matching records, not pages carrying the word.** The "result count is a real count" rule above was established on the newspapers and does not survive a personal-name query over a personal collection.

Three defences, cheapest first:

- **`--level item` collapses the fan-out exactly** — the same query returns **567 items** rather than 112,647 pages, a two-hundredfold reduction, and what comes back is a usable bibliography: *Conjurers' Monthly Magazine*, *Some modern conjuring* (1909), *Hypnotism: its history and present development* (1889).
- **Sort by date and inspect the ends.** A hit outside the subject's lifetime proves the tail is metadata. One request, and the fastest diagnosis available.
- **Confirm any book page with `snippets` before believing it.** Relevance ranking is honest — the top hits for `Houdini` were a real 1928 *New Republic* essay and a Macfadden piece — but the tail is not, and nothing in a result line separates them.

The tell, once you know it: **consecutive `sp=` numbers from one item.** Real prose does not match on pages 1, 2, 3, 4, 5 and 6 in a row.

### Page level or item level

| | `--level page` (default) | `--level item` |
|---|---|---|
| Returns | one image of one document | the whole document |
| Snippets | yes | no |
| `get` | that page | the entire text, one request |
| Metadata fan-out | multiplied by page count | one hit per document |
| Good for | *where in this book* | *what does LoC hold on this* |

`prestidigitation` is 2,611 pages against 1,662 items. Use **item** first on any name that is also a collection, contributor or subject heading — every performer whose papers LoC holds. Use **page** when the term is distinctive enough that a hit is probably a text hit, and when you need something citable.

**`get` on an item reference downloads a whole book in one request** — *Some modern conjuring* came back as 145 KB, 25,000 words — after which you grep locally for nothing and dodge the metadata trap entirely. The price: **the item text carries no page boundaries at all.** No form feeds, no image markers. You will find the passage and be unable to cite where it sits. When the citation matters, locate the page through a page-level search and quote from `snippets`; when you are only deciding whether a book repays reading, pull the item and grep.

### Traps specific to long-form material

- **Multi-volume sets lose their title.** A page of Ponsin renders as `Image 27 of Volume 1`, and the book's identity survives only in the URL slug — `gdcmassbookdig.nouvellemagiebla00pons_0`. Read the slug, not the title line.
- **`p. N` is the image number, not the printed page.** The title field says so outright: `Image 51 of …`. Front matter and plates make the two diverge, so cite the URL and let the researcher read the folio off the scan.
- **Periodical volumes are often `n.d.`** — `Image 603 of v. 45` of *Bernarr Macfadden's Joyous Life* carries no date. Any `--from-year`/`--to-year` silently discards them, so run an unbounded search too before concluding a run is absent.
- **Indexes, catalogues and dictionaries are pure citation matches.** `prestidigitation` hits page 274 of *Webster's handy-condensed dictionary*, and at item level returns *Bibliotheca Lindesiana … Catalogue of the printed books*. Books produce far more of these than newspapers do.
- **Dealer advertising is bound into the back of magic books** — *Some modern conjuring* ends with Mysto Manufacturing and W. G. Edwards, "dealers in High Class Magical Apparatus". Noise for a performer search; primary evidence for a question about apparatus and the trade.
- **Manuscript items are containers, not documents.** `prestidigitation --level item` returns *Walt Whitman Papers … Literary File, 1841-1919* — a folder, matched somewhere inside. The same fan-out applies: `clairvoyance` and `Houdini` each report exactly 2,675 pages from contributor `hockley, frederick`, which is one metadata match spread across a whole run.
- **Book OCR is cleaner than newspaper OCR in the body and worse at the edges.** Set text transcribes well; endpapers, plates and copyright stamps produce pages of noise. A hit that snippets renders as line noise is a scanned blank, not a bad query. (One 1909 English book sampled — weakly established.)

### `--subject` is a books instrument, and returns zero on newspapers

Subject headings belong to the **parent catalogue record**, not to the page — the same mechanism as the metadata fan-out above. What that record *is* decides whether the headings are worth anything:

| Material | What the headings describe | Example, on a `prestidigitation` hit |
|---|---|---|
| book | the book's content | `magic tricks`, `handbooks, manuals, etc`, `spiritualism, parapsychology` |
| newspaper | the *newspaper title* | `newspapers`, `united states`, `charlotte amalie`, `saint thomas` … |
| periodical | the run, broadly | `periodicals`, `united states`, `20th century` |
| manuscript | the containing collection | `american literature`, `whitman, walt,. leaves of grass` |

So on books it is excellent and on everything else it is place-and-genre noise. Verified: `prestidigitation --subject 'magic tricks'` returns **772**, and every one of them is a book — adding `--format newspaper` to that query returns **0**, not an error.

**That zero is the trap.** A valid heading combined with newspapers looks exactly like "this material does not exist". Never put `--subject` in a press sweep.

Where it earns its place is assembling a bibliography:

```sh
locgov search 'prestidigitation' --subject 'magic tricks' --level item
```

**You do not have to guess the headings.** Non-newspaper results print a `subjects:` line — that is where `magic tricks` and `spiritualism, parapsychology` above came from — so run the search unfiltered first, read the headings off the results, then filter by one. They are printed only for non-newspaper material, because a newspaper page inherits a dozen place names from its title and they would bury the result; `--json` still carries them for everything.

**`--title` works here too, and gives you a free control.** It takes the `partof_title` facet, which bound periodical runs carry exactly as newspapers do: `--title "conjurers' monthly magazine (new york) 1906-1908"` with no query returns **420 pages** of Houdini's own magazine. The same title with `'"second sight"'` returns 0 — and because the bare facet is proven to return 420, that 0 is a real absence rather than a mistyped filter. **Verify a facet value with an empty query before reading anything into a zero.**

## Searching in a language other than English

Search in the language of the paper. The index normalises historical orthography, so **search the modern spelling**: `Gedankenleser` matches the printed `Gedankenleſer`, and you should not search for the ſ form.

**Diacritics are folded to ASCII, in every script.** This is not a decomposition fold — it flattens letters that have no decomposition at all:

| Pair | Hits each |
|---|---|
| `schon` / `schön` | 589,247 |
| `español` / `espanol` | 146,452 |
| `człowiek` / `czlowiek` | 42,306 |
| `società` / `societa` | 43,323 |
| `טעאַטער` / `טעאטער` | 24,610 |

Polish `ł` is the proof: it is a distinct letter, not an accented `l`, and it folds anyway. Hebrew vowel points fold too. Matching is case-insensitive as well, though it is not fuzzy in general — the nonsense control `xqzptvw` returns 0.

The good half: **OCR that drops an accent costs you nothing.** `Gedankenübertragung` still finds a page whose scan lost the diaeresis, and you need not search `ue` spellings separately.

The bad half: **an accented word and its unaccented homograph are the same query.** You cannot separate them, and you can never compare spelling variants by result count when an accent is the only difference — the counts are literally the same number. This is what makes `tönnen` look like 139,320 mangled *können* when they are occurrences of *Tonnen*, "tons".

Vocabulary is the limiting factor more than syntax, and **period spelling matters more than translation.** For the German press: `Gedankenleser`, `Hellseher`, `Telepath`, `Hypnotiseur`, `Wahrsager`, `Zauberkünstler`, `Gedankenübertragung`. Verified counts elsewhere: Spanish `hipnotismo` 2,607 and `prestidigitador` 499; Italian `ipnotismo` 242 and `prestigiatore` 103; Polish `magnetyzm` 222 and `hypnotyzm` 54 — while `hipnotyzm`, the modern spelling, returns **3**. Ask for the period term.

### Yiddish is in Hebrew script, and it works

Query it in Hebrew script. It is a first-class subset, not a broken one:

- `טעאטער` returns **24,610** pages, while the Hebrew-script nonsense control `קשזחטפצ` returns 0 — so the match is literal and the corpus is genuinely indexed.
- `snippets` returns Hebrew-script keyword-in-context, right to left, with `{braces}` intact.
- `get` returns clean UTF-8 Yiddish; one sampled page held 26,106 Hebrew characters.
- **Phrase search works in Hebrew script.** `טעאטער ניו` as bare words returns 20,464; `"טעאטער ניו"` quoted returns 66. The quotes bite exactly as they do in Latin script.
- **Final and medial forms are distinct — they do not fold.** `און` returns 132,385 and `אונ` 71,756, so a word spelled with the wrong form is a different query. Unlike vowel points, which do fold, letter forms must be right.

**Transliteration does not work.** `teater` inside the Yiddish subset returns 18 hits against 24,610 for the Hebrew-script form, and `snippets` on the best of them reports *no occurrences* — the Latin-script trickle is the English matter these papers also carry, since they are catalogued `yiddish, english`, not romanised Yiddish. Compose the query in Hebrew script or do not search Yiddish at all.

## False positives and lost hits

**Fraktur's characteristic failure is k read as t or d** — but it is sporadic, and how sporadic matters as much as the pattern itself. Observed on a 1900 page of *Vorwärts*:

| OCR | Actual |
|---|---|
| `Cytlus` | Cyklus |
| `tönnte` | könnte |
| `duntler` | dunkler |
| `Glocden` | Glocken |
| `Muſithalle` | Musikhalle |
| `tieines` | kleines |
| `Facel` | Fackel |

**It is not confined to that page or that title** — `das {Tleine} Fahrzeug` for *das kleine Fahrzeug* turns up in *Die Helden von Tsingtau* (1915), a different title fifteen years later, so the pattern is a property of the corpus rather than of one bad scan.

**But it is nothing like universal, and you should not assume your k-word is broken.** In that same Tsingtau snippet, `Kommandant` and `Kapitänleutnant` both render their k correctly. Three American German-language papers sampled across 1894–1897 — *Abendblatt* (Chicago), *Washington Journal*, *Freie Presse für Texas* — returned 35 correct spellings of common k-words and no misreads at all, including `Zauberkunststückchen` with all three k's intact. The substitution tracks scan and typeface quality, not the language.

So the practical rule is a **fallback, not a first move**: search the correct spelling first, and only when a German search comes back suspiciously thin retry with `k` replaced by `t` — for `Zauberkünstler`, `Kartenkunst`, `Okkultismus` and the like. Expect the analogous problem in any language set in a blackletter or unfamiliar face; this was characterised in German because German is the largest such corpus here, not because it is unique to it.

**You cannot measure how common a misread is by comparing result counts**, because of the diacritic folding described in the previous section. `tönnen` reports 139,320 hits, which looks like overwhelming evidence for `können` being mangled — and is nothing of the kind. They are occurrences of *Tonnen*, "tons".

**f and ſ swap**: `ſühlt` for *fühlt*, `Hilſt` for *hilft*.

**Umlauts are sometimes set as a combining e**: `ungläͤubig` for *ungläubig*, which is neither `ä` nor `ae` and defeats both spellings.

**Outside German the dominant confusion differs by language**, each characterised from one sampled page:

*Yiddish* — final letters break and `ל` vanishes into `?` (*Der Morgen zshurnal*, 1929-03-31 p.8):

| OCR | Actual |
|---|---|
| `אוז` | און |
| `מעז`, `כען` | מען |
| `טעאמער`, `סעאטער` | טעאטער |
| `אפּרי?` | אפּריל |
| `פּאבי?יק` | פּאבליק |
| `האָטע?` | האָטעל |

This one is not a rare defect. `אוז`, the corrupt form of *un* ("and"), appears on **129,741 of the 132,713 Yiddish pages** — 98% — and is indexed as its own token, so nothing folds it back to `און` (132,385). Verified in context: a snippet reading `סיטי {אוז} קאנטרי`, "city *un* country".

Confirmed on a second title a decade earlier — *Yidishes ṭageblaṭṭ*, 1919-11-07 p.7 — which carried 39 Hebrew words containing `?` (`האבע?`, `זא?`, `וויי?`, `ל?עבען`) and ran `און` 121 against `אוז` 18. So the rate is roughly 13–19% on the commonest word in the language, across two papers thirty years apart.

**A Yiddish term ending in a final letter, or containing `ל`, is the one most likely to be missed**, and a `?` inside a Yiddish OCR word almost always stands for `ל`.

*Polish* — **c read as o**: `leoz` for *lecz*, `jeszoze` for *jeszcze*, `szozyt` for *szczyt*, `ekstatyoznyoh` for *ekstatycznych*, `pomooą` for *pomocą*. Separately `ń` becomes `ó`: `łaóouch` for *łańcuch*. The other Polish diacritics survive well.

*Spanish* — **n read as u**: `uua` for *una*, `uu` for *un*, `reclansaudo` for *reclamando*, `inaudado` for *mandado*. Also `easo` for *caso*, `cea` for *sea*.

*Italian* — **i, l and the digit 1 collapse**: `11` for *il* (eight times against 32 correct on one page), `I!` and `II` for *Il*, `Instltute` for *Institute*, `migliala` for *migliaia*.

**The Latin-script papers drop the line-end hyphen entirely, and both halves fall out of the index.** This is the largest single source of lost hits outside German, and it works differently from Fraktur. The sampled Spanish, Polish and Italian pages carried **zero** `~`, `—` or `-` end-of-line markers — the word is simply split with nothing to mark it, so `get` has nothing to rejoin. One Spanish page had 449 such breaks: `sá`/`bados`, `convencio`/`nales`, `aten`/`ción`, `hip`/`notista`.

Proven against the index rather than inferred: `snippets` on that page for `sábados convencionales atención` matched **only** `atención` — the two words plainly present but broken were not findable. So **a long word is materially less likely to be found than a short one**, and a thin result for `prestidigitador` is partly an artefact of length. When a search in these languages comes back thin, try a shorter distinctive stem or a co-occurring short word before concluding the material is absent.

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
