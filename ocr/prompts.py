ACCESSION_JOURNAL_PROMPT = """
You are transcribing a scanned page from a historical German library accession
journal (Akzessionsjournal), dated by the year given in the page header. Your
task is OCR-style literal transcription into CSV — not correction, not
expansion, not interpretation, DO NOT CORRECT OR MODERNIZE.

OUTPUT SCOPE
- Produce exactly one CSV, one row per book/accession entry.
- Do NOT include the page's top header row (e.g. the year, or a month label
  sitting alone as a page/column heading) as a data row.
- Do NOT include any footer/summary/totals row (e.g. rows containing
  aggregate totals, sums, or counts like "21 Anl." at the bottom of the
  page). Detect these by their position (bottom of table) and content
  (aggregate numbers, no accession number, no title).
- If uncertain whether a row is a summary row vs. a real entry, include it
  and note the doubt in the row_confidence column rather than silently
  dropping it.
- Treat each page image as fully self-contained. Do NOT rely on or assume
  any information from other pages. All month headers and ditto chains
  must be resolvable using only what is visible on this page.

TRANSCRIPTION RULES (apply to every column)
- Transcribe exactly what is written, character for character, including:
  - Abbreviations as written (e.g. "o.J.", "Bd.", "Aufl.", "gbd.") — do NOT
    expand them.
  - Multi-line entries within a single cell (e.g. a title continuing on a
    second physical line) — merge into one cell as continuous text, with a
    single space between the lines. Do not treat it as a new row, and do
    not insert a line-break character.
  - Interlineations / insertions above the line — transcribe inline in the
    position they clearly belong (e.g. inserted before the word it
    modifies), but do not mark them typographically.
  - Struck-through, corrected, or overwritten numbers — transcribe the final
    visible/intended reading only, as a plain value (no brackets, no
    strikethrough notation), EXCEPT for entire cancelled/struck-through
    entries, which are still transcribed normally but flagged in
    unusual_marks (see below).
- Do NOT translate anything. Do NOT modernize spelling or punctuation.
- Do NOT silently fix obvious errors in the source (wrong dates, odd
  spacing, etc.) — transcribe what is on the page, except for ditto
  resolution as specified below.
- Do NOT insert confidence markers, brackets, or question marks into
  individual cells. All uncertainty is captured once, per row, in the
  final "row_confidence" column only.

DITTO MARKS — GENERAL PRINCIPLE
Any ditto mark (", u, do., -"-, "ders[elbe]", "dies[elbe]", "dass[elbe]" etc.)
stands in for something specific that the scribe considered unchanged from a 
previous row — not necessarily an entire cell. Before resolving a ditto mark, 
think about what piece of information it is plausibly repeating, given the 
structure of what's written around it, and resolve only that piece.

- If a whole cell is just a ditto mark with nothing else written in it,
  resolve the entire cell from the nearest preceding row (in that same
  column, on this same page) that has an explicit, non-ditto value.
- If a cell contains a ditto mark ALONGSIDE some explicitly written text,
  the scribe is signaling that part of the entry repeats while another
  part is new. Identify which part is being held constant (the ditto) and
  which part is new (the explicit text), and construct the resolved cell
  by combining: the relevant piece pulled forward from the nearest
  preceding row, plus the newly written piece exactly as written.
  This applies wherever the pattern occurs — for example, but not limited
  to: a vendor/source name repeating while the date changes; an author
  name repeating while the title changes; a format or edition note
  repeating while a volume number changes. Use judgment based on what
  clearly stayed the same and what was clearly written fresh, rather than
  applying a fixed template to specific columns.
- Never let a ditto mark cause you to overwrite or discard something that
  was explicitly written in that row. The explicit text always wins for
  the part of the cell it covers; only the unwritten, ditto-marked part is
  pulled from a previous row.


COLUMN STRUCTURE NOTE
The data column, second from the left, ("day") has no per-row month value. Instead, a
single month abbreviation (e.g. "Jan.") appears once, as a header sitting
above that column, and applies to every day value beneath it on this page.
Treat this month header as fixed context for the whole page, not as a
per-row field to transcribe.

SPECIAL CASE: THE "date" COLUMN
This is a derived field, not a literal single-cell transcription:
- Take the (already ditto-resolved) day value from the row.
- Take the month from the column header above the day column (e.g. "Jan."),
  as written on this page — do not expand it.
- If there is a year in the column header, use that; otherwise, use the year 
  printed at the top of the page.
- Format as: DAY.[MONTH YEAR]
  Example: 4.[Jan.1959]

CSV COLUMNS (in this exact order, as they appear in the scanned page)
1. accession_no    — the leftmost accession number, as written
2. date             — constructed per the SPECIAL CASE rule above
3. letter           — the letter column, literal
4. entry_text       — the full bibliographic citation cell, literal,
                       ditto-resolved per the general principle above
                       (e.g. author repeating while title changes)
5. source_note      — dealer/source name + date, literal, ditto-resolved
                       per the general principle above (e.g. vendor
                       repeating while date changes)
6. mark             — a symbol in the mark column, literal
7. price            — the price figure, literal
8. fraction         — a column containing usually a fraction 
9. subject_group    — the subject group column, literal
10. quantity         — the quantity/count column, literal
11. binding_note    — remarks like "gbd.", "1", etc., literal
12. row_confidence  — one value for the whole row: "high", "medium", or
                       "low", reflecting your overall certainty reading
                       this row (handwriting legibility, ambiguous
                       corrections, unclear or partial ditto resolution,
                       etc.)
13. unusual_marks   — short, literal, comma-separated description of any
                       anomaly in the row, or empty if none. Covers:
                       - CANCELLATION: the entire row/entry is struck
                         through or otherwise voided in the source.
                         e.g. "entry struck through"
                       - COLOR/INK ADDITION: part of the row appears
                         added in a different color/ink than the main
                         entry (e.g. a circled cell).
                         e.g. "price circled in red"
                       - MARGINAL / INTERLINEAR NOTE: a handwritten note
                         not part of the normal columns, appearing to be
                         a later addition. Transcribe the note text
                         literally here (not in entry_text).
                         e.g. "marginal note: 'unbekannt'"
                       - OVERWRITE / RENUMBERING: the accession number or
                         another field appears corrected or overwritten.
                         e.g. "accession no. appears overwritten"
                       - PARTIAL DITTO AMBIGUITY: as described above.
                       - OTHER: any other visibly unusual feature, briefly
                         and literally described.
                       Do not interpret WHY a mark was made — describe
                       only what is visibly there. If multiple anomalies
                       apply, separate with a semicolon in one cell.
14. source_page     — the page identifier provided to you for this image
                       (echo it back exactly as given; if none was given,
                       leave empty)

FORMATTING
- Output as TAB-SEPARATED values (TSV), not comma-separated. Use a single
  literal tab character (\t) between fields.
- Do NOT use commas as the field delimiter — commas will appear naturally
  within fields (e.g. author/title citations, dealer names with dates) and
  must NOT be escaped, quoted, or removed. Transcribe them exactly as part
  of the field's text.
- Do not wrap fields in quotation marks. No quoting is needed since tabs
  are the delimiter.
- If a field would ever need to contain a literal tab character (rare),
  replace it with a single space instead.
- Leave a cell empty (not "N/A", not "-") if nothing is written there in
  the source — unless the source itself contains a literal "-", which you
  should transcribe as-is.
- Output only raw TSV: one header row, then one row per entry, fields
  separated by tabs. No code fences, no commentary, no explanations before
  or after the output.

DIACRITIC WARNING — U WITH A DISTINGUISHING MARK VS. UMLAUT Ü
Historical German handwriting frequently places a small line or
above a lowercase "u" purely to distinguish it visually from "n" or
from adjacent minim strokes (m, i, etc.) — this is a common period
handwriting convention and is NOT an umlaut.
- An umlaut "ü" has TWO DISTINCT DOTS above the letter.
- A plain "u" disambiguation mark is a SINGLE CURVED LINE or hook, not
  two dots.
- Look carefully at the shape of the mark before transcribing. Do not
  default to "ü" just because there is some mark above a u — verify it is
  specifically two separate dots before transcribing it as ü. If the mark
  is a single line, transcribe as plain "u".

CRITICAL: DO NOT AUTOCORRECT TO A "MORE LIKELY" WORD OR NAME
You will encounter surnames, place names, and words that are unusual,
archaic, or not in common use. Do NOT substitute what you believe is the
"more plausible" or more familiar-looking word or name, even if the
handwritten form looks similar to a common word/name and even if you are
confident the common form is what was "probably meant." Silently correcting 
it to the more familiar name is a serious error, not a helpful fix. 
If a word is genuinely ambiguous between two readings, transcribe your
best reading of the actual letters on the page (not the more common word)
and lower row_confidence to reflect the uncertainty.

"""


def build_prompt(source_page: str | None = None) -> str:
    """
    Returns the full prompt text for a single page.

    Args:
        source_page: identifier for the page image (e.g. filename), echoed
                     back into the source_page column of the output CSV.
    """
    if source_page:
        return ACCESSION_JOURNAL_PROMPT + f"\n\nsource_page for this image: {source_page}\n"
    return ACCESSION_JOURNAL_PROMPT