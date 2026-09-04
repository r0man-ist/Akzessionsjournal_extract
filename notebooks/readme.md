## Usage

```bash
marimo edit notebooks/accessionsjournal.py
```

CSV and JSONL inputs are provided through file uploads in the notebook UI — no hardcoded paths.
The notebook only talks to the public k10plus/stabikat SRU endpoints; no API key required.

## accessionsjournal.py

Step-by-step review of the pipeline's LLM judgments. For each row you can:

- Inspect all search queries that ran and their result counts
- Switch between queries to see which PPNs each one returned
- Run a manual SRU query and add its PPNs to the candidate list
- Open the catalogue record inline (via stabikat iframe)
- Record a verdict (`accept` / `reject` / `uncertain`) at the **record** level (PPN)
  and optionally at the **item** level (EPN + shelfmark)
- Download the accumulated verdicts as a JSONL file

Verdicts are appended as `judgment` events to a separate output JSONL,
leaving the original pipeline log untouched.

## Merging review output into the pipeline log

The notebook exports judgment events in the same JSONL format as the pipeline.
To merge, append the review log to your pipeline log:


```bash
cat abgleich_log.jsonl review_2026-09-04T....jsonl > merged_log.jsonl
```

Neither source file is modified. If you want to merge in place instead:

```bash
cat review_2026-09-04T....jsonl >> abgleich_log.jsonl
```

**Why this is safe:**

- Human verdicts have a newer `ts`, so `_latest()` in the notebook will display
  them as the authoritative verdict per `(row_id, ppn)`.
- `judge.py` skips any `(row_id, ppn)` pair that already has a judgment, so
  re-running it after merging will not overwrite human verdicts.
- `rollup.py` collects accepted PPNs from all judgment events regardless of
  `judged_by`, so human accepts are treated identically to LLM accepts.

**If you plan to re-run `retry.py` after review**, merge first — it uses
`row_judgment_summary()` to skip rows that already have an accepted PPN, and
needs to see your human verdicts to do so correctly.