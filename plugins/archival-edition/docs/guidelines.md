# Annotation guidelines for archival documents

These guidelines describe how archival documents (letters, postcards, telegrams, conference programs, manuscripts of papers and talks, notes) are encoded in TEI with the `tei-archival` schema, and how annotators review and correct the documents produced by the archival edition extractor of the PDF-TEI-Editor.

- Schema: [tei-archival.rng](https://cboulanger.github.io/pte-edition-plugin/schema/tei-archival.rng)
- Plugin and source: [cboulanger/pte-edition-plugin](https://github.com/cboulanger/pte-edition-plugin)

## Workflow

1. **Photograph** every page of the document in the archive, in reading order, including blank pages that carry stamps or notes, the envelope and any enclosures that belong to it.
2. **Fill in the Document Description Form** (one per document) in Word. Part A always, then the one part (B, C or D) that matches the document type.
3. **Build the PDF**: export the form to PDF from Word (do not print and scan it if you can avoid it; the extractor reads the exported text exactly) and append the photographs, one per page, in reading order.
4. **Extract**: upload the PDF to the PDF-TEI-Editor and run the "Archival edition" extractor with a multimodal model (Claude). The extractor fills the TEI header from the form and transcribes each photographed page.
5. **Review** the result against the photographs, following the [review checklist](#review-checklist), and save it with the appropriate status.

The extractor never invents header content: everything in the header comes from the form or from the extractor itself (`encodingDesc`, `revisionDesc`). If the header is wrong, correct the form, or correct the header and keep both in sync.

## Document structure

```xml
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>…</fileDesc>         <!-- title, responsibility, publication status, msDesc -->
    <encodingDesc>…</encodingDesc> <!-- extractor, guidelines, document type taxonomy -->
    <profileDesc>…</profileDesc>   <!-- summary, languages, keywords, document type, correspondence -->
    <revisionDesc>…</revisionDesc> <!-- extraction and later revisions -->
  </teiHeader>
  <facsimile>
    <surface xml:id="surface-1" n="1r"><graphic url="IMG_0231"/></surface>
    …
  </facsimile>
  <text xml:lang="hu">
    <body>
      <div type="letter">
        <pb n="1r" facs="#surface-1"/>
        …
      </div>
    </body>
  </text>
</TEI>
```

- One `<surface>` per photographed page. `@n` is the page label from the form's "Image files" field (`1r`, `1v`, `2r`, …), otherwise the page number.
- Every page of the transcription starts with `<pb n="…" facs="#surface-N"/>`.
- `<text xml:lang>` is the first language listed in the form. Passages in other languages are marked with `<foreign xml:lang="…">`.
- The `<div>` directly in `<body>` has the document type as `@type`: `letter`, `postcard`, `telegram`, `program`, `manuscript`, `offprint`, `notes` or `other`.

## Header

### Conventions taken over from the form

| Form convention | Encoding | Example |
| --- | --- | --- |
| Information not written on the document, in `[square brackets]` | `@ana="#inferred"`, brackets removed | `<placeName ana="#inferred">Budapest</placeName>` |
| Uncertain information, with `?` | `@cert="low"`, question mark removed | `<date when="1962-03" cert="low">1962-03</date>` |
| Date `YYYY-MM-DD`, `YYYY-MM`, `YYYY` | `@when` | `<origDate when="1962-03-12">1962-03-12</origDate>` |
| Date range `start/end` | `@notBefore`, `@notAfter` | `<date notBefore="1962-03" notAfter="1962-05">1962-03/1962-05</date>` |
| Person "Surname, Forename" | `persName` with `surname` and `forename` | `<persName><surname>Kovács</surname><forename>János</forename></persName>` |
| GND, VIAF or Wikidata id after a name | `@ref` with the authority URI | `ref="https://d-nb.info/gnd/118540238"` |
| Institution (name without a comma) | `orgName` | `<orgName>Magyar Tudományos Akadémia</orgName>` |

### Mapping of the form

| Form field | TEI |
| --- | --- |
| A1 Document ID | `fileDesc/publicationStmt/idno[@type="document-id"]` |
| A1 Document type | `profileDesc/textClass/catRef/@target` → `#doctype-letter` etc., taxonomy in `encodingDesc/classDecl` |
| A1 Title of document | `titleStmt/title` |
| A1 Descriptive title | `titleStmt/title[@type="supplied"]` |
| A1 Author(s), Corporate author | `titleStmt/author` and `msDesc/msContents/msItem/author` |
| A2 Country, City, Holding institution, Estate, Shelfmark | `msDesc/msIdentifier/country`, `settlement`, `repository`, `collection`, `idno[@type="shelfmark"]` |
| A3 Date, Source of the date, Place | `msDesc/history/origin/origDate` (`@evidence`: `internal`, `postmark`, `conjecture`, `other`), `origPlace` |
| A4 Extent, Material, Pages not photographed, Damage | `objectDesc/supportDesc/extent`, `support`, `foliation`, `condition` |
| A4 Original or copy | `objectDesc/@form`: `original`, `carbon-copy`, `photocopy`, `draft`, `transcript` |
| A4 Writing | `handDesc/handNote[@xml:id="hand-main"]` (handwritten) and/or `typeDesc/typeNote` (typewritten, printed) |
| A4 Letterhead, stamps, seals | `physDesc/additions[@type="letterhead"]` |
| A4 Later additions | `physDesc/additions[@type="later"]` and `handNote[@xml:id="hand-later"][@scope="minor"]` |
| A4 Enclosures | `physDesc/accMat` |
| A5 Language(s) | `profileDesc/langUsage/language/@ident` (ISO 639) |
| A5 Summary | `profileDesc/abstract/p` |
| A5 Keywords | `profileDesc/textClass/keywords/term` |
| A5 Names mentioned | `notesStmt/note[@type="entities"]` |
| A5 Related documents | `notesStmt/relatedItem/bibl` |
| A6 May it be published? | `publicationStmt/availability/@status`: yes → `free`, no → `restricted`, unclear → `unknown` |
| A6 Reason for any restriction, Rights holder | `availability/p`, `availability/licence` |
| A7 Image files | `facsimile/surface/graphic/@url`, `surface/@n` |
| A7 Photographed by, Form filled in by | `titleStmt/respStmt` with `resp` "photography" / "metadata", the date in `resp/@when` |
| A7 Other remarks | `notesStmt/note` |
| B Sender(s), Place and Date of sending, Written on behalf | `correspDesc/correspAction[@type="sent"]` with `persName`/`orgName`, `placeName`, `date`, `persName[@role="scribe"]` |
| B Addressee(s), Place and Date of receipt | `correspDesc/correspAction[@type="received"]` |
| B Answers / Answered by which letter | `correspDesc/correspContext/ref[@type="replyTo"]`, `ref[@type="repliedBy"]` |
| C Name, Dates and Place of the event | `sourceDesc/biblStruct/monogr/meeting` with `date` and `placeName` |
| C Organiser(s), Publisher | `monogr/respStmt` (resp "organiser"), `monogr/imprint/publisher` |
| C Role of the estate's creator | `notesStmt/note[@type="participation"]` |
| D Stage of the text | `msDesc/msContents/msItem/note[@type="stage"]` |
| D Occasion | `profileDesc/creation` |
| D Later published, Differs from published version | `msDesc/additional/listBibl/bibl[@type="published"]` with `note[@type="differences"]` |

The extractor adds a `respStmt` for the automatic transcription (resp "automatic transcription", with provider and model), the `encodingDesc` with the extractor and these guidelines, and a `revisionDesc/change` for the extraction. The editor adds a `respStmt` and a `change` for every annotator who saves a revision.

## Transcription

### Principles

- **Diplomatic transcription.** Keep the spelling, punctuation, capitalization, abbreviations, word division and errors of the original. Do not normalize, modernize, correct or translate in the text itself; use `<choice>` if a correction or expansion is needed (see below).
- **Lines.** Every new line of the source starts with `<lb/>`. A word divided across a line break gets `<lb break="no"/>` inside the word; a hyphen written at the end of the line is kept before it.

  ```xml
  <p><lb/>Köszönöm a különle<lb break="no"/>nyomatot, nagy örömmel</p>
  ```

- **Pages.** Each page starts with `<pb n="1r" facs="#surface-1"/>`. A paragraph that runs across a page break is split into two `<p>`, the first with `part="I"`, the second with `part="F"`.
- **Layout** is not reproduced beyond lines and pages. Indentation, centering and spacing are ignored unless they carry meaning (then `@rend`, e.g. `rend="center"`).

### Hungarian

- Check the accented vowels carefully: á é í ó ö ő ú ü ű. Models and annotators confuse ő/ö and ű/ü most often.
- Older typewriters and some hands write õ, û or ô for ő and ű. Transcribe what is written; if the reading is clear, do not add a `<choice>`.
- Abbreviations common in letters (e.g. `sz.`, `u.`, `ill.`, `ld.`, `dr.`, `ny. r. tanár`) are kept as written; expand with `<choice><abbr>…</abbr><expan>…</expan></choice>` only where the expansion is not obvious to a reader.

### Uncertain and illegible text

| Situation | Encoding |
| --- | --- |
| Reading likely but not certain | `<unclear cert="medium">szívesen</unclear>` |
| Reading doubtful | `<unclear cert="low">Kálmán</unclear>` |
| Illegible | `<gap reason="illegible" quantity="2" unit="words"/>` |
| Lost (torn, cut off, faded) | `<gap reason="damage" quantity="1" unit="lines"/>` or `<damage agent="tear"><unclear>…</unclear></damage>` |
| Text supplied by the editor | `<supplied reason="damage">…</supplied>` |

Never silently guess. A `<gap>` is better than a confident wrong reading.

### Corrections by the writer and later hands

| Situation | Encoding |
| --- | --- |
| Struck through | `<del rend="strikethrough">…</del>` |
| Overwritten | `<subst><del rend="overwritten">a</del><add place="inline">e</add></subst>` |
| Added above or below the line | `<add place="above">…</add>`, `<add place="below">…</add>` |
| Added in the margin | `<add place="margin-left">…</add>` |
| Added later by another hand (pencil notes, archive numbers) | `<add hand="#hand-later" place="…">…</add>` |
| Underlined, superscript, spaced | `<hi rend="underline">…</hi>`, `<hi rend="superscript">…</hi>`, `<hi rend="spaced">…</hi>` |
| Printed letterhead, stamps, archive notes | `<fw type="letterhead">…</fw>`, `<fw type="stamp">…</fw>`, `<fw type="archive-note">…</fw>` |
| Errors of the writer that need comment | `<choice><sic>…</sic><corr>…</corr></choice>` |

### Names and dates in the text

Tag the names an annotator should recognise (see "Names mentioned" in the form) with `<persName>`, `<placeName>` and `<orgName>`, and dates with `<date>`. In the text, add `@ref` with a GND, VIAF or Wikidata URI only when the identification is certain, and `@when` only for complete dates.

```xml
<p><lb/>Tegnap beszéltem <persName ref="http://www.wikidata.org/entity/Q…">Szabó professzorral</persName>
<lb/>a <placeName>bécsi</placeName> konferenciáról.</p>
```

## Document types

### Letters, postcards and telegrams

```xml
<div type="letter">
  <pb n="1r" facs="#surface-1"/>
  <fw type="letterhead">MAGYAR TUDOMÁNYOS AKADÉMIA …</fw>
  <opener>
    <dateline><placeName>Budapest</placeName>, <date when="1962-03-12">1962. márc. 12.</date></dateline>
    <lb/><salute>Kedves Jane!</salute>
  </opener>
  <p><lb/>…</p>
  <closer>
    <salute>Szívélyes üdvözlettel</salute>
    <lb/><signed>Teszt Elek</signed>
  </closer>
  <postscript><p><lb/>U.i. …</p></postscript>
</div>
```

- The address on an envelope or the address side of a postcard goes into its own `<ab type="address">` or `<address><addrLine>…</addrLine></address>` after the `<pb>` of that page.
- Postmarks and receipt stamps: `<fw type="stamp">`.

### Conference programs and other printed matter

Use `<head>` for headings, `<list><item>` for schedules and lists of speakers, and `<ab>` for other blocks. Handwritten additions by the estate's creator (ticks, underlinings, notes) are `<add hand="#hand-later">` or `<hi rend="underline" hand="#hand-later">`.

### Manuscripts of papers and talks, notes

Use `<head>` for headings, `<p>` for paragraphs, `<list>` for points, and `<note place="margin-left|margin-right|foot">` for marginal and foot notes. Deletions and additions are frequent in drafts; encode them as above, and use `<subst>` where an addition replaces a deletion.

## Review checklist

1. **Header against the form:** document ID, title, author, date (`@when`/`@notBefore`/`@notAfter`), place, shelfmark, publication status. Are the brackets and question marks of the form reflected in `@ana` and `@cert`?
2. **Pages:** one `<pb>` per photograph, with the right page label and `@facs`.
3. **Text against the photograph, line by line:** every word, accent and punctuation mark; line breaks; words divided across lines.
4. **Uncertainty:** every doubtful reading in `<unclear>`, every illegible passage a `<gap>`; nothing guessed silently. Check every `<unclear>` the model produced and remove it if the reading is certain.
5. **Corrections and hands:** deletions, additions, later hands.
6. **Structure:** opener, closer, postscript, headings, lists; paragraphs split across pages have `part="I"`/`part="F"`.
7. **Names and dates** tagged; authority `@ref` only where certain.
8. **Validation:** the editor shows no schema errors.
9. **Language:** `<text xml:lang>` and `<foreign xml:lang>` are correct.
