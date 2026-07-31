---
name: loc-search
description: Search the Library of Congress with the `locgov` CLI — American newspapers from 1736 to 1963 in more than twelve languages, plus digitised books and manuscripts, all with page-level full text through one API. Use it for the American reception of a performer, the foreign-language immigrant press, and the conjuring literature of the Library.
---

# Library of Congress

One API with no key over each item that the Library of Congress digitised and transcribed: **newspapers from 1736 to 1963**, **digitised books**, and **manuscript collections**. Each item has a full-text index, and each item resolves to the individual page.

Use it for the American part of a career — the tour circuit, local notices, and articles that explain methods. It is the counterpart to Gallica and ANNO. Two properties make it different:

- **It is not only newspapers.** The books and the manuscripts are in the same index, and they search in the same way. Thus the conjuring literature and the personal papers come back together with the press. A search of everything is the default, and `--collection` is how you make the search narrow.
- **It is not only English.** The newspaper corpus holds many languages. The American immigrant press published in more languages than most national archives hold.

## Coverage by language

The pages in the newspaper collection, from its own language facet:

| | | | |
|---|---|---|---|
| english 22,499,675 | german 619,712 | spanish 453,914 | polish 169,005 |
| french 135,671 | yiddish 132,713 | italian 88,547 | czech 58,960 |
| norwegian 49,635 | serbian 46,789 | | |

Each language searches in the same way. The community that came to a performance in the United States wrote about the performer, so the Spanish, Polish and Yiddish press are not a small detail. Frequently they hold a notice that the English papers did not print.

**The shape of each decade is very different for each language, and it decides if a subset is worth a search.** Each column sums to the total for that language exactly, so these are counts and not estimates:

| Decade | german | spanish | polish | yiddish | italian |
|---|---|---|---|---|---|
| 1880s | | 22,933 | 1,642 | 1 | — |
| 1890s | 103,779 | 44,278 | 22,010 | 296 | 3,974 |
| 1900s | 128,127 | 63,073 | 39,083 | **0** | 24,033 |
| 1910s | 177,394 | 66,021 | 70,108 | 24,719 | 34,400 |
| 1920s | 24,075 | 70,765 | 31,847 | 24,178 | 6,705 |

Read the empty cells as facts about the collection, not as facts about your query. **The Yiddish subset has no material from the 1900s.** A Yiddish search limited to that decade gives zero results. That is the coverage. It is not OCR, and it is not an error. Yiddish starts in quantity in 1910 and is largest in the 1940s (46,873). Polish falls after 1929 and stops completely by 1949. Italian is largest in the 1910s and falls to 6,705 in the 1920s. Only Spanish is dense across the full period 1880–1930, and only Spanish continues in quantity after 1930.

## Commands

```sh
locgov search "<query>" [--pages N|N-M|all] [filters] [--json]
locgov snippets <reference> "<query>"   # the query in context on that page
locgov get <reference>                  # OCR text, prints path to the cached file
```

The filters for `search` are `--from-year`, `--to-year`, `--language`, `--state`, `--title`, `--format`, `--contributor`, `--subject`, `--collection`, `--level`, `--per-page` and `--sort`.

`--sort` takes `relevance` (default), `date_asc` or `date_desc`.
`--collection chronicling-america` limits the search to the newspapers. Leave it out to search everything.

A **reference** is the loc.gov URL that the tool prints with each result. It is the citation link, the argument to `snippets`, the argument to `get`, and an address that a human can put into a browser to see the scan.

**A search resolves to a page, not to a document.** This is true for a book and for a manuscript exactly as for a newspaper, so there is no step from document to page to pay for. A result already says *page 25 of this book*, and `snippets` changes that into *and here is the sentence*:

```
$ locgov snippets 'https://www.loc.gov/resource/gdc.00198495517/?sp=25' 'second sight'
# https://www.loc.gov/resource/gdc.00198495517/?sp=25
  matched: second, sight
    ... among others the experiment called “{Second} {Sight}” Now-a-days we can easily
    explain this so-called {Second} {Sight}, which in the ‘40's and '50's attracted the
    attention of the whole civilized world. ...
        https://www.loc.gov/resource/gdc.00198495517/?sp=25&q=second%20sight
```

The matched terms come back in `{braces}`.

## Query syntax — read this before you plan a search

The tool joins bare words with **AND**. `"quoted phrases"` match exactly.

**There is no OR. There is no NOT.** This is the defining limit of this source, and it is invisible if you do not know it. The server **removes** `OR`, `NOT`, a `-` at the start, parentheses and `|` from the query. It does not reject them. Confirmed:

| Query | Results |
|---|---|
| `hypnotism` | 44,089 |
| `hypnotism doctor` | 18,865 |
| `hypnotism -doctor` | 18,865 |
| `hypnotism NOT doctor` | 18,865 |

The last three rows are the same AND query. A search in the form `(Gedankenleser OR Hellseher)` gives the pages that hold **both** words. This is a few pages in place of hundreds. The server reports this as a normal result, and nothing warns you.

**Consequence: do one search for each variant.** The habit that is correct for ANNO and DDB, to put each spelling into one `(A OR B OR C)` query, is actively incorrect here, and it will quietly remove most of a search. Plan one request for each variant instead. Note that `--per-page 150` makes each request cheap.

**Watch the shell.** `locgov search "Brooklyn Bridge"` is an AND search, because the shell removes the quotation marks. For a phrase, the quotation marks must survive: `locgov search '"Brooklyn Bridge"'`. On one 1883 sample, that is the difference between 11,098 results and 2,363 results.

## The result count is a real count

loc.gov filters the results. It does not rank them. Its totals are honest: the decade facet counts sum to exactly the reported total (44,089 for `hypnotism`). Thus:

- **You can give a total as a count.** "2,363 pages hold the phrase Brooklyn Bridge" is a true statement. The equivalent statement on Gallica is not true.
- **`--sort date_asc` is safe on each query.** There is no relevance tail that hides the good material.
- **`--pages all` has a meaning**, but see the cost below.

**This is true for the newspapers. It is not true for the books.** There, a page-level total counts the matches in the metadata and repeats each one across every page of an item. `Houdini` reports 112,647 pages of digitised books and 567 actual items. Read **Books, periodicals and manuscripts** below before you give any total that includes long documents.

## How to be complete

**`--per-page 150`** is the default and the maximum, so a full search costs much less than on the fixed 10 of ANNO. 517 results is four requests, not fifty-two.

Make the query narrow before you collect the results. The tests confirm each filter below:

- `--from-year` and `--to-year` — **note the risk**: the credible `start_date` and `end_date` parameters that appear in third-party examples are *silently ignored* by loc.gov. This client never sends them. It sends the `dates=YYYY/YYYY` form, which loc.gov accepts. If you ever build a URL by hand, do the same.
- `--language` takes the facet name in English — `german`, `spanish`, `polish`, `yiddish`, `italian`, `czech`, `french`. It intersects with `--state`.
- `--title` takes the **exact** title string that the second line of a result prints, for example `'der deutsche correspondent (baltimore, md.) 1841-1918'`. It reduced one query from 359 to 105.
- `--format` takes the material type — `newspaper`, `book`, `periodical`, `manuscript/mixed material`. To separate the books from the newspapers is more important here than it sounds. See below.
- `--contributor` takes a contributor facet exactly. This is how you reach the named collections of the Library.
- `--subject` takes a Library of Congress subject heading — **books only, see below**.
- `--collection chronicling-america` excludes the books and the manuscripts. `--level item` gives full documents in place of pages.

**A facet value with an incorrect spelling gives 0. It does not give the unfiltered set.** `--format xqzptvw` and `--contributor 'not a real contributor'` both give zero. The server does not remove the filter without a message, so a spelling error in a facet fails loudly. This is the opposite of the `start_date` risk. Thus, when a zero surprises you, compare it against the bare facet before you believe it.

You can get results to at least number 20,000. The documentation of loc.gov warns of degradation after 100,000.

## Books, periodicals and manuscripts

A search includes them by default, and for this subject they are not the smaller half of the source. The page counts, through `--format`:

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

`"Robert-Houdin"` is more than two times stronger in the books than in the press, and `prestidigitation` gives 778 French pages against 1,817 English pages. **The Library holds the conjuring literature itself, in French and in English.** Ponsin's *Nouvelle magie blanche dévoilée* (1853) and Robert-Houdin's *Confidences et révélations* (1868) are both there in full text.

**`--collection selected-digitized-books` is the limit to use**, and it covers bound periodical runs as well as books: `prestidigitation` gives 1,070 pages there.

**The two conjuring collections are not collections. They are contributors.** The *Harry Houdini Collection* and the *McManus-Young Collection* of the Library give much of this material — 718 pages and 672 pages of the 2,611 for `prestidigitation` — but there is no `/collections/harry-houdini-collection/` to limit the search to. Reach them with `--contributor`:

```sh
locgov search 'prestidigitation' --contributor 'harry houdini collection (library of congress)'
```

The value must be exact and lowercase, and it must include the text in parentheses. That query gives 718 pages, which is the library of Houdini himself. It is the nearest thing to a curated conjuring collection that this source has.

### The metadata risk — read this before you give any count of books

**On a long document, a page-level search matches the *metadata* of the item as well as its text. It then reports that one match one time for each page.** This is the defining hazard here, and the output does not show it.

Confirmed: `Houdini` inside `selected-digitized-books` reports **112,647 pages**. In `date_asc` order, the first six results are pages 1 to 6 of *An essay towards a theory of apparitions*, published in **1813**, which is sixty-one years before the birth of Houdini. `snippets` on page 3 gives *no occurrences of Houdini*. The book is in the Harry Houdini Collection, and one match in the provenance became a result on each page of the book.

Thus, for the books, and not for the newspapers, **a total counts matching records, not pages that hold the word.** The rule "the result count is a real count" above comes from the newspapers, and it does not survive a query for a personal name over a personal collection.

Three defences, with the lowest cost first:

- **`--level item` removes the repetition exactly.** The same query gives **567 items** in place of 112,647 pages, a reduction by a factor of two hundred, and the output is a usable bibliography: *Conjurers' Monthly Magazine*, *Some modern conjuring* (1909), and *Hypnotism: its history and present development* (1889).
- **Sort by date, and examine the two ends.** A result outside the life of the subject proves that the tail is metadata. This costs one request, and it is the fastest diagnosis available.
- **Confirm each book page with `snippets` before you believe it.** The relevance order is honest: the top results for `Houdini` were a real 1928 essay in the *New Republic* and an article by Macfadden. But the tail is not honest, and nothing in a result line separates the two.

The signal, when you know it: **consecutive `sp=` numbers from one item.** Real text does not match on pages 1, 2, 3, 4, 5 and 6 in sequence.

### Page level or item level

| | `--level page` (default) | `--level item` |
|---|---|---|
| Gives | one image of one document | the full document |
| Snippets | yes | no |
| `get` | that page | the full text, one request |
| Metadata repetition | multiplied by the page count | one result for each document |
| Good for | *where in this book* | *what does LoC hold on this* |

`prestidigitation` is 2,611 pages against 1,662 items. Use **item** first for each name that is also a collection, a contributor or a subject heading — that is, each performer whose papers the Library holds. Use **page** when the term is distinctive enough that a result is probably a match in the text, and when you need something to cite.

**`get` on an item reference downloads a full book in one request.** *Some modern conjuring* came back as 145 KB and 25,000 words. You can then use grep locally at no cost, and you avoid the metadata risk completely. The price is this: **the item text has no page boundaries.** There are no form feeds and no image markers. You will find the passage and you will not be able to cite its position. When the citation is important, find the page with a page-level search and quote from `snippets`. When you only decide if a book is worth a reading, take the item and use grep.

### Risks specific to long documents

- **A set of several volumes loses its title.** A page of Ponsin appears as `Image 27 of Volume 1`, and the identity of the book survives only in the URL slug — `gdcmassbookdig.nouvellemagiebla00pons_0`. Read the slug, not the title line.
- **`p. N` is the image number, not the printed page number.** The title field says this directly: `Image 51 of …`. The front matter and the plates make the two numbers different, so cite the URL and let the researcher read the folio number from the scan.
- **A periodical volume frequently has no date**, shown as `n.d.` `Image 603 of v. 45` of *Bernarr Macfadden's Joyous Life* carries no date. Any `--from-year` or `--to-year` filter removes these items with no message, so also do a search with no date limits before you conclude that a run is absent.
- **An index, a catalogue and a dictionary give citation matches only.** `prestidigitation` matches page 274 of *Webster's handy-condensed dictionary*, and at item level it gives *Bibliotheca Lindesiana … Catalogue of the printed books*. The books give far more of these matches than the newspapers do.
- **Publishers bind dealer advertisements into the back of magic books.** *Some modern conjuring* ends with Mysto Manufacturing and W. G. Edwards, "dealers in High Class Magical Apparatus". These pages are unwanted results for a search about a performer. They are primary evidence for a question about apparatus and the trade.
- **Manuscript items are containers, not documents.** `prestidigitation --level item` gives *Walt Whitman Papers … Literary File, 1841-1919*, which is a folder with a match somewhere inside it. The same repetition applies: `clairvoyance` and `Houdini` each report exactly 2,675 pages from the contributor `hockley, frederick`. That is one metadata match spread across a full run.
- **The OCR of books is cleaner than the OCR of newspapers in the body, and worse at the edges.** The set text transcribes well. The endpapers, the plates and the copyright stamps give pages of noise. When `snippets` shows a result as line noise, the page is a blank scan. Your query is not bad. (One English book of 1909 sampled, so this is weakly established.)

### `--subject` is an instrument for books, and it gives zero on newspapers

The subject headings belong to the **parent catalogue record**, not to the page. This is the same mechanism as the metadata repetition above. What that record *is* decides if the headings have value:

| Material | What the headings describe | Example, on a `prestidigitation` result |
|---|---|---|
| book | the content of the book | `magic tricks`, `handbooks, manuals, etc`, `spiritualism, parapsychology` |
| newspaper | the *title of the newspaper* | `newspapers`, `united states`, `charlotte amalie`, `saint thomas` … |
| periodical | the run, in general terms | `periodicals`, `united states`, `20th century` |
| manuscript | the collection that holds the item | `american literature`, `whitman, walt,. leaves of grass` |

Thus on books this filter is excellent, and on everything else it gives place-and-genre noise. Confirmed: `prestidigitation --subject 'magic tricks'` gives **772** results, and each one is a book. Add `--format newspaper` to that query and it gives **0**, not an error.

**That zero is the risk.** A correct heading with the newspapers looks exactly like "this material does not exist". Never put `--subject` in a search of the press.

Its value is in the construction of a bibliography:

```sh
locgov search 'prestidigitation' --subject 'magic tricks' --level item
```

**You do not have to guess the headings.** Results that are not newspapers print a `subjects:` line. That is the origin of `magic tricks` and `spiritualism, parapsychology` above. Do the search with no filter first, read the headings from the results, then filter by one heading. The tool prints the headings only for material that is not a newspaper, because a newspaper page receives a dozen place names from its title and they would hide the result. `--json` still carries the headings for each type of material.

**`--title` is also usable here, and it gives you a check that costs no extra request.** It takes the `partof_title` facet, and a bound periodical run carries this facet exactly as a newspaper does. `--title "conjurers' monthly magazine (new york) 1906-1908"` with no query gives **420 pages** of the magazine of Houdini himself. The same title with `'"second sight"'` gives 0. The bare facet gives 420, so that 0 is a real absence and not an error in the filter. **Confirm a facet value with an empty query before you make a conclusion from a zero.**

## How to search in a language other than English

Search in the language of the paper. The index normalises the orthography of the period, so **search the modern spelling**: `Gedankenleser` matches the printed `Gedankenleſer`. Do not search for the ſ form.

**The index folds each diacritic to ASCII, in each script.** This is not a fold of decomposed characters. It also flattens letters that have no decomposition:

| Pair | Results, each |
|---|---|
| `schon` / `schön` | 589,247 |
| `español` / `espanol` | 146,452 |
| `człowiek` / `czlowiek` | 42,306 |
| `società` / `societa` | 43,323 |
| `טעאַטער` / `טעאטער` | 24,610 |

The Polish `ł` is the proof. It is a separate letter, not an `l` with an accent, and the index folds it. The index also folds the Hebrew vowel points. The match ignores capital letters, but it is not fuzzy in general: the nonsense control `xqzptvw` gives 0.

The good half of this behaviour: **an OCR error that loses an accent costs you nothing.** `Gedankenübertragung` still finds a page whose scan lost the diaeresis, and you do not need a separate search for the `ue` spellings.

The bad half: **a word with an accent and its homograph without the accent are the same query.** You cannot separate them, and you can never compare spelling variants by their result counts when an accent is the only difference. The counts are literally the same number. This is why `tönnen` looks like 139,320 incorrect scans of *können*, when they are occurrences of *Tonnen*, "tons".

The vocabulary limits you more than the syntax, and **the spelling of the period is more important than the translation.** For the German press, use `Gedankenleser`, `Hellseher`, `Telepath`, `Hypnotiseur`, `Wahrsager`, `Zauberkünstler` and `Gedankenübertragung`. Counts confirmed elsewhere: Spanish `hipnotismo` 2,607 and `prestidigitador` 499; Italian `ipnotismo` 242 and `prestigiatore` 103; Polish `magnetyzm` 222 and `hypnotyzm` 54, while `hipnotyzm`, the modern spelling, gives **3**. Ask for the term of the period.

### Yiddish is in Hebrew script, and the index holds it correctly

Write the query in Hebrew script. This is a first-class subset, not a broken one:

- `טעאטער` gives **24,610** pages, and the nonsense control in Hebrew script `קשזחטפצ` gives 0. Thus the match is literal, and the index truly holds the corpus.
- `snippets` gives keyword-in-context in Hebrew script, from right to left, with the `{braces}` intact.
- `get` gives clean UTF-8 Yiddish. One sampled page held 26,106 Hebrew characters.
- **You can do a phrase search in Hebrew script.** `טעאטער ניו` as bare words gives 20,464. `"טעאטער ניו"` with quotation marks gives 66. The quotation marks have the same effect as in Latin script.
- **The final and medial forms of a letter are different, and the index does not fold them.** `און` gives 132,385 and `אונ` gives 71,756, so a word with the incorrect form is a different query. The index folds the vowel points, but the letter forms must be correct.

**Do not use transliteration. It does not find the Yiddish text.** `teater` inside the Yiddish subset gives 18 results against 24,610 for the Hebrew-script form, and `snippets` on the best of them reports *no occurrences*. The small number of Latin-script results is the English material that these papers also carry, because the catalogue records them as `yiddish, english` and not as romanised Yiddish. Write the query in Hebrew script, or do not search Yiddish.

## False positives and lost results

**The characteristic failure of Fraktur is a k that reads as t or d.** But it is not regular, and how irregular it is matters as much as the pattern. Observed on a 1900 page of *Vorwärts*:

| OCR | Actual |
|---|---|
| `Cytlus` | Cyklus |
| `tönnte` | könnte |
| `duntler` | dunkler |
| `Glocden` | Glocken |
| `Muſithalle` | Musikhalle |
| `tieines` | kleines |
| `Facel` | Fackel |

**This is not limited to that page or that title.** `das {Tleine} Fahrzeug` for *das kleine Fahrzeug* appears in *Die Helden von Tsingtau* (1915), a different title fifteen years later. Thus the pattern is a property of the corpus, not of one bad scan.

**But it is not universal, and you must not assume that your k-word is incorrect in the index.** In that same Tsingtau snippet, `Kommandant` and `Kapitänleutnant` both hold their k correctly. Three American German-language papers sampled across 1894–1897 — *Abendblatt* (Chicago), *Washington Journal* and *Freie Presse für Texas* — gave 35 correct spellings of common k-words and no incorrect ones, including `Zauberkunststückchen` with all three k characters intact. The substitution follows the quality of the scan and the typeface, not the language.

Thus the practical rule is a **second attempt, not a first move**. Search the correct spelling first. Only when a German search gives very few results, search again with `t` in place of `k` — for `Zauberkünstler`, `Kartenkunst`, `Okkultismus` and similar words. Expect the same problem in each language set in a blackletter face or an unfamiliar face. The tests measured this in German because German is the largest such corpus here, not because it is unique to German.

**You cannot measure how frequent an OCR error is by a comparison of result counts**, because of the fold of the diacritics in the previous section. `tönnen` reports 139,320 results, which looks like strong evidence that the OCR damages `können`. It is not. They are occurrences of *Tonnen*, "tons".

**f and ſ exchange**: `ſühlt` for *fühlt*, and `Hilſt` for *hilft*.

**An umlaut is sometimes set as a combining e**: `ungläͤubig` for *ungläubig*, which is neither `ä` nor `ae`, and which defeats both spellings.

**Outside German the dominant confusion is different for each language.** The tests measured each one from one sampled page.

*Yiddish* — the final letters break, and `ל` becomes `?` (*Der Morgen zshurnal*, 1929-03-31 p.8):

| OCR | Actual |
|---|---|
| `אוז` | און |
| `מעז`, `כען` | מען |
| `טעאמער`, `סעאטער` | טעאטער |
| `אפּרי?` | אפּריל |
| `פּאבי?יק` | פּאבליק |
| `האָטע?` | האָטעל |

This defect is not rare. `אוז`, the corrupt form of *un* ("and"), appears on **129,741 of the 132,713 Yiddish pages** — 98% — and the index holds it as its own token. Thus nothing folds it back to `און` (132,385). Confirmed in context: one snippet reads `סיטי {אוז} קאנטרי`, "city *un* country".

Confirmed on a second title ten years earlier — *Yidishes ṭageblaṭṭ*, 1919-11-07 p.7 — which carried 39 Hebrew words that hold `?` (`האבע?`, `זא?`, `וויי?`, `ל?עבען`) and gave `און` 121 times against `אוז` 18 times. Thus the rate is approximately 13–19% on the most common word in the language, across two papers thirty years apart.

**A Yiddish term that ends with a final letter, or that holds `ל`, is the term that the index most probably loses.** A `?` inside a Yiddish OCR word almost always stands for `ל`.

*Polish* — **c reads as o**: `leoz` for *lecz*, `jeszoze` for *jeszcze*, `szozyt` for *szczyt*, `ekstatyoznyoh` for *ekstatycznych*, and `pomooą` for *pomocą*. Separately, `ń` becomes `ó`: `łaóouch` for *łańcuch*. The other Polish diacritics survive well.

*Spanish* — **n reads as u**: `uua` for *una*, `uu` for *un*, `reclansaudo` for *reclamando*, and `inaudado` for *mandado*. Also `easo` for *caso*, and `cea` for *sea*.

*Italian* — **i, l and the digit 1 become one character**: `11` for *il* (eight times against 32 correct on one page), `I!` and `II` for *Il*, `Instltute` for *Institute*, and `migliala` for *migliaia*.

**The papers in Latin script lose the hyphen at the end of a line completely, and the index loses both halves of the word.** This is the largest single cause of lost results outside German, and its effect is different from Fraktur. The sampled Spanish, Polish and Italian pages carried **zero** `~`, `—` or `-` markers at the end of a line. The OCR simply divides the word with no marker, so `get` has nothing to join. One Spanish page had 449 such breaks: `sá`/`bados`, `convencio`/`nales`, `aten`/`ción`, and `hip`/`notista`.

The tests proved this against the index, and did not infer it. `snippets` on that page for `sábados convencionales atención` matched **only** `atención`. The index could not find the two words that are clearly present but divided. Thus **the index loses a long word more frequently than a short word**, and a small result for `prestidigitador` is partly a consequence of its length. When a search in these languages gives very few results, try a shorter distinctive stem, or a short word that occurs with it, before you conclude that the material is absent.

**English-language OCR fails in more ordinary ways** — broken words, lost punctuation, and `rowpond.-d` for *responded*. But the quantity of English text is large, so the usual problem is too many results, not lost results. A phrase search has much more value than an AND search on common words.

## The cached text is normalised, and the snippets are not

`locgov get` changes two things, so that a grep of the file matches in the same way as the index:

- **It joins the hyphenation at the end of a line.** The marker is `~`, `—` or `—~`, and *not* a plain hyphen. One sampled page of *Vorwärts* had 94 tildes, 13 em dashes and zero hyphens. Thus `ſchön~\nſten` becomes `schönsten`.
- **It folds a long ſ to s**, which is the standard convention for a transcription of Fraktur. Before this change, `grep Gedankenleser` on a German page gave **nothing**, and the page held seven occurrences.

The output of `snippets` is **not** normalised. It comes directly from the service, and it still shows `Gedankenleſer`, because a quotation must read as the page prints it. Quote from the snippets. Use grep on the cached file.

## Risks specific to this source

- **Snippets need a page-level reference, not an item.** Each page — newspaper, book or manuscript — has them. A full item does not, because the service sends its transcription as one file with no divisions. `locgov snippets` refuses an item with an explanation, and it costs no request. `--level page` is the default, so this only affects you when you asked for `--level item`.
- **`get` follows the same division.** A page reference downloads that one page. An item reference downloads the full document in one file. Both are one request, so a full book has a low cost. But examine which one you asked for before you conclude that a file of 1 KB means a page with little text.
- **The tool excludes unreadable material by default.** `search` limits the results to items whose text the client can receive, because a result that you cannot read has no use. `--include-unreadable` removes that limit, and the output then marks each unreadable item.
- **Stop after an HTTP 403 from a normal search. Do not send the request again.** The HTML pages are behind an anti-bot wall, and the JSON API is not. A 403 means a block, not a bad query.
- **Truncated responses and lost responses both occur.** The client tries one more time, and then reports honestly. A failure that continues is a real outage. Do not try to work around it.

## Cost

The client permits **one request every four seconds**, with one request at a time, and all processes share this limit. Therefore parallel subagents share one budget. Change the interval with `LOC_MIN_REQUEST_INTERVAL` only when you have a reason.

**Do not send more than 20 requests each minute.** The Library publishes this limit and enforces it strictly. It blocks an IP address that goes above the limit. The block continues for one full hour. That penalty, and not politeness, is why the default is 15 requests each minute. A block of one hour in the middle of research costs far more than the speed that you save.

Plan the budget in requests. `search` is one request for each result page of up to 150 results. `snippets` and `get` are one request each, plus one lookup for each reference. The client keeps this record on disk. A search also fills the record for each result that it gives, so a search and then a `snippets` command cost nothing more. The client keeps the downloads in a cache under `$XDG_CACHE_HOME/loc-mcp`.

If the requests start to fail, stop. Then tell the user. Do not send the request again. Record in each report that you did not search this source.
