import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    import json
    from collections import Counter

    import sys
    from pathlib import Path

        # notebook lives in notebooks/, utils/ lives one level up in the project root
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from utils.jsonl_log import EventLogger
    from utils.jsonl_log import EventLogger

    return Counter, EventLogger, io, json, mo, pd


@app.cell
def _(mo):
    mo.md("""
    # Provenienzerschließung für Akzessionsjournale
    """)
    return


@app.cell
def _(mo):
    upload = mo.ui.file(filetypes=[".csv"], kind="area", label="CSV-Datei laden")
    mo.vstack([
        mo.md("""## CSV-Datei hochladen
        Laden Sie die strukturierte, bereinigte CSV-Datei mit den bibliographischen
        Angaben aus dem Akzessionsjournal (ohne Treffer-/PPN-Spalten)."""),
        upload,
    ])
    return (upload,)


@app.cell
def _(io, mo, pd, upload):
    uploaded_file = upload.value[0]  # single-file upload
    df = pd.read_csv(
        io.BytesIO(uploaded_file.contents),
        sep=";",
        dtype=str,
        encoding="utf-8",
    )
    input_table = mo.ui.table(df, selection="single")
    mo.vstack([input_table, mo.md("""### Wählen sie aus der Tabelle eine Zeile""")])
    return (input_table,)


@app.cell
def _(mo):
    jsonl_upload = mo.ui.file(filetypes=[".jsonl"], kind="area", label="JSONL-Log laden")
    mo.vstack([
        mo.md("""## JSONL-Log laden
        Laden Sie die zur CSV gehörige Logdatei mit den Suchergebnissen (abgleich_log.jsonl)."""),
        jsonl_upload,
    ])
    return (jsonl_upload,)


@app.cell
def _(io, json, jsonl_upload):
    def build_candidate_index(contents: bytes) -> dict[str, dict[str, dict]]:
        """
        row_id -> {query_name: {n_results, ppns, template, query}}

        Keeps the latest non-skipped sru_search event per (row_id, query_name).
        Only reads results, never mutates anything on disk.
        """
        index: dict[str, dict[str, dict]] = {}
        text = io.BytesIO(contents).read().decode("utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("step") != "sru_search" or e.get("status") == "skipped_empty":
                continue
            index.setdefault(e["row_id"], {})[e["query_name"]] = {
                "n_results": e.get("n_results", 0),
                "ppns": e.get("ppns", []),
                "template": e.get("template"),
                "query": e.get("query"),
            }
        return index

    candidate_index = build_candidate_index(jsonl_upload.value[0].contents)
    return (candidate_index,)


@app.cell
def _(input_table):
    selected_row = input_table.value
    row = selected_row.iloc[0]
    row_id = str(row["Lfd. Nr."])
    return row, row_id, selected_row


@app.cell
def _(mo, row):
    mo.vstack([
        mo.md(f"**{col}:** {value}")
        for col, value in row.iloc[:6].items()
    ])
    return


@app.cell
def _(candidate_index, mo, row_id):
    candidates = candidate_index.get(row_id, {})
    mo.stop(not candidates, mo.md(f"⚠️ Keine Suchergebnisse im Log für Zeile {row_id}"))
    return (candidates,)


@app.cell
def _(Counter, candidates):
    # how many different queries returned each PPN for this row
    ppn_overlap = Counter()
    for _info in candidates.values():
        ppn_overlap.update(set(_info["ppns"]))
    return (ppn_overlap,)


@app.cell
def _(candidates, pd, row):
    expected = pd.to_numeric(row["Zahl"], errors="coerce")

    def diff_key(name):
        n = candidates[name]["n_results"]
        if pd.isna(expected) or n == 0:
            return (float("inf"), 1)
        d = n - expected
        return (abs(d), 0 if d >= 0 else 1)

    ranked_names = sorted(candidates.keys(), key=diff_key)
    closest_name = ranked_names[0] if ranked_names else None
    return closest_name, ranked_names


@app.cell
def _(candidates, closest_name, mo, ppn_overlap, ranked_names, row):
    def label(name):
        info = candidates[name]
        shared = sum(1 for p in info["ppns"] if ppn_overlap[p] > 1)
        note = f", {shared} auch in anderen Anfragen" if shared else ""
        return f"{name}  ·  {info['n_results']} Treffer{note}"

    option_labels = {label(name): name for name in ranked_names}

    query_selector = mo.ui.radio(
        options=option_labels,
        value=label(closest_name) if closest_name else None,
        inline=True,
        label="Anfrage wählen:",
    )

    mo.vstack([mo.md(f"**{row.get('Zahl', '?')} Bände erwartet**"), query_selector])
    return (query_selector,)


@app.cell
def _(candidates, query_selector):
    chosen_name = query_selector.value
    PPN_selected = candidates[chosen_name]["ppns"] if chosen_name else []
    return PPN_selected, chosen_name


@app.cell
def _(PPN_selected, mo):
    mo.md(f"""
    Mit der gewählten Suchanfrage wurden {len(PPN_selected)} Treffer gefunden mit den PPNs {PPN_selected}
    """)
    return


@app.cell
def _(PPN_selected, mo):
    button = mo.ui.button(
        value=0,
        on_click=lambda v: (v + 1) % max(len(PPN_selected), 1),
        label="Nächste PPN",
        kind="warn",
    )
    button
    return (button,)


@app.cell
def _(PPN_selected, button):
    selected_PPN = PPN_selected[button.value] if PPN_selected else None
    return (selected_PPN,)


@app.cell
def _(mo, selected_PPN):
    stabikat_url = (
        f"https://stabikat.de/Search/Results?lookfor=id%3A{selected_PPN}&type=AllFields"
        if selected_PPN else "https://stabikat.de/"
    )
    mo.iframe(stabikat_url, height=600)
    return


@app.cell
def _(mo, selected_row):
    _rows = [
        mo.hstack([mo.md(f"**{col}**"), mo.md(str(selected_row.iloc[0][col]))])
        for col in selected_row.columns
    ]
    metadata_view = mo.vstack([mo.md(f"### Zeile {selected_row.index[0]}")] + _rows)
    metadata_view
    return


@app.cell
def _(mo):
    mo.md("""
    ## Exemplardaten
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    TODO
    - for PPN in accepted PPNs (from judgments in the log):
     - query_sru
     - extract Item information
     - list EPN and shelfmark
     - check if there are 361-fields!
     - log epns and signature as their own event (not yet: writing to CSV)
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Entscheidung speichern
    """)
    return


@app.cell
def _(mo):
    logger_path = mo.ui.text(value="abgleich_log.jsonl", label="JSONL-Log (Schreibziel)")
    logger_path
    return (logger_path,)


@app.cell
def _(EventLogger, logger_path):
    logger = EventLogger(logger_path.value)
    return (logger,)


@app.cell
def _(chosen_name, logger, mo, row_id, selected_PPN):
    get_message, set_message = mo.state("")

    def save_judgment(_):
        if selected_PPN is None:
            set_message("⚠️ Keine PPN ausgewählt")
            return
        logger.log(
            row_id, "judgment",
            query_name=chosen_name,
            ppn=selected_PPN,
            judged_by="human",
            verdict="accept",
        )
        set_message(f"✅ PPN {selected_PPN} als korrekt geloggt (Zeile {row_id})")

    save_button = mo.ui.button(
        label="PPN als korrekt bestätigen",
        kind="success",
        on_click=save_judgment,
    )
    save_button
    return (get_message,)


@app.cell
def _(get_message, mo):
    mo.md(get_message())
    return


if __name__ == "__main__":
    app.run()
