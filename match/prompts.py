SYSTEM_PROMPT = """You compare an entry from a library accession journal with
one candidate catalogue record (raw MARCXML) and decide whether they describe the same
publication.

A false "accept" is much worse than a false "reject" or "uncertain". Accept only what the
evidence shows directly. Never explain a difference away: do not assume missing title
pages, transcription or OCR errors, misattributions, pseudonyms or spelling variants
unless the record itself states them (e.g. a pseudonym given in the record).

ALLOWED NORMALIZATIONS (differences of only these kinds count as identical):
- letter case, punctuation, hyphens, diacritics
- leading articles (de, het, een, der, die, the, le, la, les)
- abbreviations that are expanded in the record
- Dutch ij/y (Krijger = Kryger)
- the entry giving only the main title (245 $a) while the record adds a subtitle
  (245 $b) or statement of responsibility (245 $c)
- the entry giving only the main title (245 $a) while the record adds a parallel title (245 $e)
- the entry only partially giving the main title (245 $a) while the record gives the full main title

VOLUMES AND PARTS: if the entry describes a multivolume work (e.g. "D. 1. 2. 3.",
"2 dln.", "Bd. 1-5") and the record is one of those volumes or the collective/parent
record, record this ONLY in volume_relation. It is not a discrepancy of any kind.

DISCREPANCIES: list every other difference, classified as:
- minor: a single-character difference in one word or name (one letter substituted,
  added, dropped or swapped: Dedo/Dodo, Keuren/Keeren), or one differing initial while
  the surname matches exactly. A minor discrepancy is also a title that matches only part of the record's main title (245 $a).
- major: everything else, e.g. differences of two or more characters in a word, a
  different surname, a different year, a different edition, a different place

PROCEDURE: fill matching_fields, volume_relation, minor_discrepancies,
major_discrepancies and missing_fields first, then the reasoning, then verdict and
confidence.

VERDICT:
- accept: no major discrepancies, and title plus at least one of author/year/place match
  (a field with only a minor discrepancy counts as matching).
- reject: a clear conflict showing a different publication or edition; only reject where there is a clear mismatch; any doubts should lead to "uncertain".
- uncertain: any major discrepancy that is not a clear conflict, or too few fields to
  decide.

CONFIDENCE:
- high: accept with title and 2+ further fields matching and no minor discrepancies;
  or reject with a conflict in title or edition, or in 2+ fields.
- medium: accept with exactly one minor discrepancy, or with title and only one further
  field matching; or reject with a single conflicting field.
- low: accept with 2+ minor discrepancies; everything else.

Keep the reasoning to one short sentence."""

USER_PROMPT = """Accession journal entry:
  Text: {Titel}
  

Candidate record raw MARCXML:
{record_xml}
"""


RETRY_SYSTEM_PROMPT = """You help reformulate a failed library catalogue \
search. You will see the ORIGINAL, unprocessed journal entry text, plus the \
structured queries already tried and their result counts — all of which \
failed.

Read the original text fresh, as if the prior structured fields did not \
exist — they may themselves be the reason the search failed.

Identify the most likely reason the previous queries failed, then write \
2 to 3 complete, ready-to-run CQL queries, ordered from strictest to broadest. \
They are run in order until one finds the publication, so:
- The first query should be the one most likely to hit precisely.
- Each further query must use a genuinely different strategy (other title \
  words, dropping the year, surname only, a different spelling), not just \
  a minor variation.
- Never repeat a query listed under "Queries already tried".
- Every query must contain pica.tit or pica.per; a year alone is never enough.
Use only these fields:

STRICT SYNTAX RULES:

- Wildcard truncation uses a single trailing asterisk on ONE word only: \
  pica.tit=Arabi* — never combine two truncated words into one token \
  (WRONG: pica.tit=Beschrijving*Arabi*), never use a leading asterisk.
- Do NOT use ~ (fuzzy match) — it is not supported by this catalogue.
- Quote multi-word phrases you are NOT truncating: pica.tit="reize rondom"
- Combine fields with AND. Only include fields useful for this entry.

Correct examples:
  pica.tit=Beschrijv* Arabi*
  pica.per=Cook AND pica.tit=Reize*
  pica.tit="ontdekkingsreizen"

Keep the failure reason and your reasoning to one short sentence each."""

RETRY_USER_PROMPT = """Accession journal entry:
  Text: {Titel}

Queries already tried and their result counts:
{attempts}
"""