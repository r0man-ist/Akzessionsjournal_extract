from __future__ import annotations
import argparse
import re
from pathlib import Path

import pandas as pd

from utils.sru import prepare_cql_string, run_query, build_year_or_clause
from utils.normalize_years import normalize_years
from utils.jsonl_log import EventLogger

RAW_PLACEHOLDER_RE = re.compile(r"\{!([^{}]+)\}")
PLACEHOLDER_RE = re.compile(r"\{([^{}!][^{}]*)\}")


def fill_template(template: str, row: pd.Series, df_columns: list[str]) -> tuple[str | None, list[str]]:
    missing = []

    def replace_quoted(match: re.Match) -> str:
        column = match.group(1)
        if column not in df_columns:
            raise ValueError(f"Column '{column}' referenced in query '{template}' not found in CSV")
        value = prepare_cql_string(row[column])
        if value == "":
            missing.append(column)
        return value

    def replace_raw(match: re.Match) -> str:
        column = match.group(1)
        if column not in df_columns:
            raise ValueError(f"Column '{column}' referenced in query '{template}' not found in CSV")
        value = row[column]
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing.append(column)
            return ""
        return str(value)

    filled = RAW_PLACEHOLDER_RE.sub(replace_raw, template)
    filled = PLACEHOLDER_RE.sub(replace_quoted, filled)

    if missing:
        return None, missing
    return filled, []


def query_name(template: str) -> str:
    quoted_columns = PLACEHOLDER_RE.findall(template)
    raw_columns = RAW_PLACEHOLDER_RE.findall(template)
    columns = quoted_columns + raw_columns
    return "_".join(columns) if columns else re.sub(r"\W+", "_", template)[:30]


def run_batch(df: pd.DataFrame, templates: list[str], catalogue: str,
              logger: EventLogger, uid_col: str,
              exclude_digitised: bool = True, year_col: str | None = None,
              year_clause_col: str = "Jahr_CQL",
              skip_done: set[tuple[str, str]] | None = None) -> None:
    df = df.copy()
    skip_done = skip_done or set()

    if uid_col not in df.columns:
        raise ValueError(f"UID column '{uid_col}' not found in CSV")

    for _, row in df.iterrows():
        row_id = str(row[uid_col])

        year_clause = ""
        if year_col:
            raw_year_value = row[year_col]
            result = normalize_years(raw_year_value)
            if result["ok"]:
                year_clause = build_year_or_clause(result["years"])
            elif not result["empty"]:
                logger.log(row_id, "year_normalize_failed", raw_value=raw_year_value, error=result["error"])

        row = row.copy()
        row[year_clause_col] = year_clause

        for template, name in zip(templates, [query_name(t) for t in templates]):
            if (row_id, "sru_search", name) in skip_done:
                continue

            query, missing = fill_template(template, row, list(df.columns) + [year_clause_col])

            if query is None:
                logger.log(row_id, "sru_search", query_name=name, template=template,
                        catalogue=catalogue, status="skipped_empty",
                        missing_columns=missing)
                continue

            nr_of_records, ppns = run_query(query, catalogue=catalogue,
                                            exclude_digitised=exclude_digitised)
            logger.log(row_id, "sru_search", query_name=name, template=template,
                    query=query, catalogue=catalogue,
                    n_results=nr_of_records, ppns=ppns)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_csv")
    parser.add_argument("output_jsonl", type=Path, nargs="?", default=Path("abgleich_log.jsonl"))
    parser.add_argument("--catalogue", choices=["k10plus", "stabikat", "VD17"], default="stabikat")
    parser.add_argument("--query", action="append", default=[],
                         help='CQL template with {ColumnName} placeholders, e.g. '
                              '"pica.tit={Titel} AND {!Jahr_CQL}". Repeatable.')
    parser.add_argument("--no-exclude-digitised", action="store_true")
    parser.add_argument("--sep", default=";")
    parser.add_argument("--year-col", default=None,
                         help="Column holding a year or range, normalized via normalize_years, "
                              "available in templates as {!Jahr_CQL}")
    parser.add_argument("--uid-col", default="Nr")
    args = parser.parse_args()

    if not args.query:
        parser.error('At least one --query is required, e.g. --query "pica.tit={Titel} AND {!Jahr_CQL}"')

    df = pd.read_csv(args.input_csv, sep=args.sep, dtype=str)
    df = df.where(pd.notna(df), None)  # replace all NaN with None, DataFrame-wide

    with EventLogger(args.output_jsonl) as logger:
        skip_done = logger.already_done()
        run_batch(df, args.query, catalogue=args.catalogue, logger=logger,
                  uid_col=args.uid_col, exclude_digitised=not args.no_exclude_digitised,
                  year_col=args.year_col, skip_done=skip_done)
        run_id = logger.run_id

    print(f"Logged events for {len(df)} rows to {args.output_jsonl} (run_id={run_id})")


if __name__ == "__main__":
    main()

"""python match.py bestand.csv abgleich_log.jsonl \
    --catalogue "k10plus" (default: stabikat) \
    --year-col "Jahr" \
    --uid-col "Nr" \
    --query "pica.tit={Titel} AND {!Jahr_CQL}"""