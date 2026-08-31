# Bibliographic Matching Pipeline

A pipeline for matching bibliographic references against library catalogues
using SRU search, candidate ranking, and LLM-based judgment.

## Pipeline Overview
ocr.py → structure.py → match.py → rank.py → judge.py → retry.py


### 1. OCR (`ocr.py`)
Transcribes page images into a raw CSV using an LLM vision model.

```bash
python ocr.py
```

Input/output paths are configured in `ocr/config.py`.

### 2. Structure (`structure.py`)
Parses raw bibliographic reference strings into structured fields
(title, author, year, place, etc.) using an LLM.

```bash
# First run
python structure.py --input input.csv --output output.csv --column Titel

# Resume after a stop or crash
python structure.py --input input.csv --output output.csv --column Titel --resume
```

### 3. Match (`match.py`)
Runs CQL queries against a library catalogue for each row and logs
the results (PPNs and result counts) to a JSONL file.

Searches using a Year-column can apply normalization and range-expansion using {!Jahr_CQL}

```bash
python match.py output.csv log.jsonl \
    --catalogue k10plus \
    --year-col Jahr \
    --uid-col Nr \
    --query "pica.tit={Titel} AND {!Jahr_CQL}" \
    --query "pica.per={Autor} AND pica.tit={Titel}"
```

Safe to re-run — already completed rows are skipped automatically.

### 4. Rank (`rank.py`)
Reads the JSONL log, ranks candidate PPNs per row by specificity and
plausibility, and appends `ranking` events to the same JSONL.

```bash
python rank.py output.csv log.jsonl \
    --uid-col "Lfd. Nr." \
    --expected-col Zahl \
    --tolerance 3.0
```

### 5. Judge (`judge.py`)
Fetches the full catalogue record for each best-ranked candidate and uses
an LLM to verdict each one as `accept`, `reject`, or `uncertain`.
Appends `judgment` events to the JSONL.

```bash
python judge.py output.csv log.jsonl \
    --uid-col "Lfd. Nr." \
    --catalogue k10plus
```

Safe to re-run — already judged `(row_id, ppn)` pairs are skipped automatically.

### 6. Retry (`retry.py`)
For rows where no candidate was accepted, asks the LLM to diagnose
the failure, proposes a new query, and re-runs the judge step.
Runs up to 2 LLM retry attempts per row.

```bash
python retry.py output.csv log.jsonl \
    --uid-col "Lfd. Nr." \
    --expected-col Zahl \
    --catalogue k10plus
```

## Configuration

Each step has its own config file:

- `ocr/config.py` — model, image extensions, input/output paths
- `structure/config.py` — model, token limits, input/output paths, input column
- `match/config.py` — model, token limits, API settings for judge and retry steps (configuration for judge and retry alike)

API keys are loaded from a `.env` file



## Output

All steps append to the same JSONL log file. Each line is one event with
a `step` field (`sru_search`, `ranking`, `judgment`, etc.), a `row_id`,
a `run_id`, and a timestamp. This makes every run fully resumable and
auditable.