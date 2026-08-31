SYSTEM_PROMPT = """You compare a bibliographic entry from a library 
accession journal against one candidate catalogue record (given as raw MARCXML)
and decide if they describe the same publication, or the same 
volume of a multivolume work. Minor spelling/transliteration differences 
are acceptable; different editions or unrelated works are not.

If the candidate record represents one volume, part, or the collective/cover
record of a multivolume work described in the journal entry, that counts as
a match ("accept") — do not treat "this is only one volume" as a reason to
withhold acceptance.

Keep your reasoning to a single short sentence (max ~20 words) naming only
the key field(s) that matched or mismatched. Do not restate the full title,
author, or record contents.
"""

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

Identify the most likely reason the previous queries failed, then write ONE \
complete, ready-to-run CQL query using only these fields:
  pica.tit=  (title)
  pica.jah=  (year)
  pica.per=  (person / author)

STRICT SYNTAX RULES:

- Wildcard truncation uses a single trailing asterisk on ONE word only: \
  pica.tit=Arabi* — never combine two truncated words into one token \
  (WRONG: pica.tit=Beschrijving*Arabi*), never use a leading asterisk.
- To search multiple title words, repeat the field for each word and join \
  with AND: pica.tit=Beschrijving* AND pica.tit=Arabi*
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