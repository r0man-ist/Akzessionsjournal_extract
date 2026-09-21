import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    import json
    from datetime import datetime, timezone
    from collections import defaultdict
    import urllib.request
    import urllib.parse
    import xml.etree.ElementTree as ET
    import anywidget
    import traitlets

    return (
        ET,
        anywidget,
        datetime,
        defaultdict,
        io,
        json,
        mo,
        pd,
        timezone,
        urllib,
    )


@app.cell
def _(mo):
    mo.md("""
    # Provenienzerschließung · Manuelle Überprüfung
    """)
    return


@app.cell
def _(mo):
    upload_csv = mo.ui.file(filetypes=[".csv"], kind="area", label="Strukturierte CSV laden")
    upload_jsonl = mo.ui.file(filetypes=[".jsonl"], kind="area", label="JSONL-Log laden")

    mo.vstack([
        mo.md("## Dateien"),
        mo.hstack([upload_csv, upload_jsonl], justify="start", gap=2)
    ])
    return upload_csv, upload_jsonl


@app.cell
def _(mo):
    get_log, set_log = mo.state([])
    return get_log, set_log


@app.cell
def _(io, mo, pd, upload_csv):
    mo.stop(not upload_csv.value, mo.md("⬆️ Bitte CSV hochladen"))
    _f = upload_csv.value[0]
    df = pd.read_csv(io.BytesIO(_f.contents), sep=";", dtype=str, encoding="utf-8")
    df = df.where(pd.notna(df), None)
    return (df,)


@app.cell
def _(defaultdict, io, json, mo, upload_jsonl):
    mo.stop(not upload_jsonl.value, mo.md("⬆️ Bitte JSONL hochladen"))
    raw_text = io.BytesIO(upload_jsonl.value[0].contents).read().decode("utf-8")
    all_events: list[dict] = []
    for _line in raw_text.splitlines():
        if _line.strip():
            all_events.append(json.loads(_line))

    def _latest(events, key_fn):
        index = {}
        for e in events:
            key = key_fn(e)
            if key is None:
                continue
            existing = index.get(key)
            if existing is None or e.get("ts", "") > existing.get("ts", ""):
                index[key] = e
        return index

    # Index: row_id -> list of all events in file order
    events_by_row: dict[str, list[dict]] = defaultdict(list)
    for _e in all_events:
        events_by_row[_e["row_id"]].append(_e)

    # Latest ranking event per row
    latest_ranking = _latest(
        (e for e in all_events if e.get("step") == "ranking"),
        key_fn=lambda e: e["row_id"],
    )

    # All sru_search events per row (not skipped)
    searches_by_row: dict[str, list[dict]] = defaultdict(list)
    for _e in all_events:
        if _e.get("step") == "sru_search" and _e.get("status") != "skipped_empty":
            searches_by_row[_e["row_id"]].append(_e)

    # Latest judgment per (row_id, ppn) — by timestamp
    judgments_by_row_ppn = _latest(
        (e for e in all_events if e.get("step") == "judgment"),
        key_fn=lambda e: (e["row_id"], e.get("ppn")) if e.get("ppn") else None,
    )
    return (
        all_events,
        events_by_row,
        judgments_by_row_ppn,
        latest_ranking,
        searches_by_row,
    )


@app.cell
def _(df, mo):
    row_selector = mo.ui.table(df, selection="single")
    row_selector
    return (row_selector,)


@app.cell
def _(mo, row_selector):
    mo.stop(len(row_selector.value) == 0)
    selected_row = row_selector.value.iloc[0]
    selected_row_id = str(selected_row["Lfd. Nr."])
    return (selected_row_id,)


@app.cell
def _(events_by_row: dict[str, list[dict]], mo, selected_row_id):
    _events = events_by_row.get(selected_row_id, [])

    def _badge(step: str) -> str:
        colors = {
            "sru_search": "blue",
            "ranking": "green",
            "judgment": "orange",
            "retry_diagnosis": "purple",
            "monotonicity_violation": "red",
            "retry_exhausted": "red",
        }
        c = colors.get(step, "gray")
        return f'<span style="background:{c};color:#fff;border-radius:4px;padding:1px 6px;font-size:.8em">{step}</span>'

    def _fmt_event(e: dict) -> str:
        parts = [_badge(e.get("step", "?"))]
        if e.get("query"):
            parts.append(f"`{e['query']}`")
        elif e.get("template"):
            parts.append(f"template: `{e['template']}`")
        if e.get("n_results") is not None:
            parts.append(f"→ **{e['n_results']}** Treffer")
        if e.get("status"):
            parts.append(f"status: *{e['status']}*")
        if e.get("verdict"):
            parts.append(f"verdict: **{e['verdict']}** ({e.get('confidence','?')}) · judged_by: {e.get('judged_by','?')}")
        if e.get("ppn"):
            parts.append(f"PPN: `{e['ppn']}`")
        if e.get("step") == "retry_diagnosis" and e.get("failure_reason"):
            parts.append(f" {e['failure_reason']}")
        if e.get("shelfmark"):
            parts.append(f"Signatur: {e['shelfmark']}")
        if e.get("note"):
            parts.append(f"Notiz: {e['note']}")
        return "  ".join(parts)

    _lines = [f"- {_fmt_event(e)}" for e in _events]
    mo.vstack([
        mo.md("### Verlauf"),
        mo.md("\n".join(_lines) if _lines else "*Keine Ereignisse*"),
    ])
    return


@app.cell
def _(mo):
    get_manual_ppns, set_manual_ppns = mo.state([])
    return get_manual_ppns, set_manual_ppns


@app.cell
def _(selected_row_id, set_manual_ppns):
    _reset = selected_row_id
    set_manual_ppns([])
    return


@app.cell
def _(mo, selected_row_id):
    _reset = selected_row_id  # forces re-run when row changes

    manual_query_input = mo.ui.text(
        placeholder="z.B. pica.tit=Muster AND pica.jah=1920",
        label="Manuelle SRU-Anfrage",
        full_width=True,
    )
    manual_search_btn = mo.ui.run_button(label="Suchen", kind="neutral")
    mo.vstack([mo.md("### Manuelle Suche"), manual_query_input, manual_search_btn])
    return manual_query_input, manual_search_btn


@app.cell
def _(ET, manual_query_input, manual_search_btn, mo, set_manual_ppns, urllib):
    mo.stop(not manual_search_btn.value)
    mo.stop(not manual_query_input.value.strip(), mo.callout(mo.md("⚠️ Bitte eine Anfrage eingeben"), kind="warn"))
    _params = urllib.parse.urlencode({
        "version": "1.1",
        "operation": "searchRetrieve",
        "recordSchema": "marcxml",
        "maximumRecords": "50",
        "query": manual_query_input.value.strip().replace("pica.","pica.x")
    })
    _url = f"https://sru.k10plus.de/opac-de-1?{_params}"
    try:
        with urllib.request.urlopen(_url, timeout=10) as _resp:
            _xml = _resp.read().decode("utf-8")
    except Exception as _e:
        mo.stop(True, mo.callout(mo.md(f"⚠️ SRU-Anfrage fehlgeschlagen: {_e}"), kind="danger"))
    _NS = {
        "srw": "http://www.loc.gov/zing/srw/",
        "marc": "http://www.loc.gov/MARC21/slim",
    }
    _root = ET.fromstring(_xml)
    _n = int(_root.findtext("srw:numberOfRecords", "0", _NS))
    _ppns = []
    for _rec in _root.findall(".//marc:record", _NS):
        for _field in _rec.findall("marc:controlfield[@tag='001']", _NS):
            if _field.text:
                _ppns.append(_field.text.strip())
    set_manual_ppns(_ppns)
    mo.md(f"**{_n} Treffer** · {len(_ppns)} PPNs geladen")
    return


@app.cell
def _(
    latest_ranking,
    mo,
    searches_by_row: dict[str, list[dict]],
    selected_row_id,
):
    _searches = searches_by_row.get(selected_row_id, [])
    mo.stop(not _searches, mo.md("⚠️ Keine Suchanfragen im Log für diese Zeile"))

    _options = {}
    for _s in _searches:
        _label = (
            f"{_s.get('query_name','?')}  ·  "
            f"{_s.get('n_results', 0)} Treffer  ·  "
            f"`{_s.get('query') or _s.get('template','')}`"
        )

        _options[_label] = _s


    # Pre-select the ranked winner if present
    _ranked_name = latest_ranking.get(selected_row_id, {}).get("chosen_query_name")
    _default_label = next(
        (lbl for lbl, s in _options.items() if s.get("query_name") == _ranked_name),
        next(iter(_options), None),  # fall back to first
    )


    query_selector = mo.ui.radio(
        options=_options,
        value=_default_label,
        label="Suchanfrage wählen",

    )

    mo.vstack([mo.md("### Suchanfragen"), query_selector])
    return (query_selector,)


@app.cell
def _(query_selector):
    chosen_search = query_selector.value
    ppns_for_query = chosen_search.get("ppns", []) if chosen_search else []
    return (ppns_for_query,)


@app.cell
def _(
    get_manual_ppns,
    judgments_by_row_ppn,
    mo,
    ppns_for_query,
    selected_row_id,
):
    _manual = get_manual_ppns()
    _all_ppns = list(dict.fromkeys(ppns_for_query + _manual))
    mo.stop(not _all_ppns, mo.md("*Keine PPNs für diese Anfrage*"))

    def _ppn_label(ppn: str) -> str:
        key = (selected_row_id, ppn)
        j = judgments_by_row_ppn.get(key)
        _tag = " 🔍" if ppn in _manual and ppn not in ppns_for_query else ""
        if j:
            verdict = j.get("verdict", "?")
            conf = j.get("confidence", "?")
            by = j.get("judged_by", "?")
            emoji = {"accept": "✅", "reject": "❌", "uncertain": "❓"}.get(verdict, "❔")
            reasoning = j.get("reasoning")
            return f"{ppn}{_tag}  {emoji} {verdict} ({conf}) · {by}:   {reasoning}"
        return f"{ppn}{_tag}"

    _options = {_ppn_label(p): p for p in _all_ppns}
    ppn_selector = mo.ui.radio(options=_options, label="PPN auswählen")
    mo.vstack([mo.md("### PPNs"), ppn_selector])
    return (ppn_selector,)


@app.cell
def _(ppn_selector):
    selected_ppn = ppn_selector.value
    return (selected_ppn,)


@app.cell
def _(judgments_by_row_ppn, mo, selected_ppn, selected_row_id):
    mo.stop(not selected_ppn)
    _j = judgments_by_row_ppn.get((selected_row_id, selected_ppn))
    if _j and _j.get("reasoning"):
        mo.vstack([
            mo.md("### LLM-Begründung"),
            mo.callout(mo.md(_j["reasoning"]), kind="info"),
        ])
    else:
        mo.md("*Keine LLM-Begründung vorhanden*")
    return


@app.cell
def _(mo, selected_ppn):
    mo.stop(not selected_ppn)
    _url = f"https://stabikat.de/Search/Results?lookfor=id%3A{selected_ppn}&type=AllFields"
    mo.vstack([
        mo.md(f"### Katalog · PPN `{selected_ppn}`"),
        mo.md(f"[Im Katalog öffnen ↗]({_url})"),
        mo.iframe(_url, height=550),
    ])
    return


@app.cell
def _(mo, ppn_selector):
    _reset = ppn_selector.value  # forces re-run when ppn changes
    verdict_selector = mo.ui.radio(
            options={
                "✅  Treffer bestätigen": "accept",
                "❌  Treffer ablehnen": "reject",
                "❓  Unsicher": "uncertain",
            },
            value=None,
            label="Urteil",
            inline=True,
        )


    mo.vstack([mo.md("### Entscheidung"), verdict_selector])
    return (verdict_selector,)


@app.cell
def _(mo, ppn_selector):
    _reset = ppn_selector.value  # forces re-run when ppn changes
    note_input = mo.ui.text(
            placeholder="Optionale Anmerkung …",
            label="Notiz",
            full_width=True,
        )
    note_input
    return (note_input,)


@app.cell
def _(mo):
    save_btn = mo.ui.run_button(label="Urteil speichern", kind="success")
    save_btn
    return (save_btn,)


@app.cell
def _(
    datetime,
    mo,
    note_input,
    save_btn,
    selected_ppn,
    selected_row_id,
    set_log,
    timezone,
    verdict_selector,
):
    mo.stop(not save_btn.value)
    mo.stop(not selected_ppn, mo.callout(mo.md("⚠️ Keine PPN ausgewählt"), kind="warn"))
    mo.stop(
            verdict_selector.value is None,
            mo.callout(mo.md("⚠️ Bitte ein Urteil auswählen, bevor gespeichert wird."), kind="warn"),
        )
    _event = {
        "row_id": selected_row_id,
        "step": "judgment",
        "ppn": selected_ppn,
        "judged_by": "human",
        "verdict": verdict_selector.value,
        "note": note_input.value or None,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    set_log(lambda events: events + [_event])
    mo.md(f"✅ PPN `{selected_ppn}` → **{verdict_selector.value}** (Zeile {selected_row_id})")
    return


@app.cell
def _(mo, selected_ppn, urllib):
    mo.stop(not selected_ppn)

    _params = urllib.parse.urlencode({
        "version": "1.1",
        "operation": "searchRetrieve",
        "recordSchema": "marcxml",
        "maximumRecords": "1",
        "query": f"pica.xppn={selected_ppn}",
    })
    _url = f"https://sru.k10plus.de/opac-de-1?{_params}"

    try:
        with urllib.request.urlopen(_url, timeout=10) as _resp:
            record_xml = _resp.read().decode("utf-8")
    except Exception as _e:
        record_xml = None
        mo.stop(True, mo.callout(mo.md(f"⚠️ SRU-Anfrage fehlgeschlagen: {_e}"), kind="danger"))

    mo.md(f"✅ Record geladen für PPN `{selected_ppn}` · [`{_url}`]({_url})")
    return (record_xml,)


@app.cell
def _(ET, mo, record_xml):
    mo.stop(not record_xml)

    _NS = {"marc": "http://www.loc.gov/MARC21/slim"}
    _root = ET.fromstring(record_xml)

    _items = []
    for _field in _root.findall(".//marc:datafield[@tag='924']", _NS):
        _epn = _field.findtext("marc:subfield[@code='a']", namespaces=_NS)
        _shelfmark = _field.findtext("marc:subfield[@code='g']", namespaces=_NS)
        if _epn:
            _items.append({"epn": _epn, "shelfmark": _shelfmark or "—"})

    mo.stop(not _items, mo.callout(mo.md("⚠️ Keine Exemplare gefunden"), kind="warn"))

    mo.md(f"**{len(_items)} Exemplar(e) gefunden**")

    _options = {
        f"{item['epn']}  ·  {item['shelfmark']}": item
        for item in _items
        }

    item_selector = mo.ui.radio(
        options=_options,
        label="Exemplar wählen",
        )
    item_selector
    return (item_selector,)


@app.cell
def _(item_selector, mo):
    _reset = item_selector.value  # forces re-run when item changes
    item_verdict_selector = mo.ui.radio(
    options={
        "✅  Treffer bestätigen": "accept",
        "❌  Treffer ablehnen": "reject",
        "❓  Unsicher": "uncertain",
    },
        value=None,
    label="Exemplar-Urteil",
    inline=True,
    )
    item_note_input = mo.ui.text(
    placeholder="Optionale Anmerkung …",
    label="Notiz",
    full_width=True,
    )
    mo.vstack([item_verdict_selector, item_note_input])
    return item_note_input, item_verdict_selector


@app.cell
def _(mo):
    item_save_btn = mo.ui.run_button(label="Exemplar-Urteil speichern", kind="success")
    item_save_btn
    return (item_save_btn,)


@app.cell
def _(item_selector):
    selected_item = item_selector.value
    return (selected_item,)


@app.cell
def _(
    datetime,
    item_note_input,
    item_save_btn,
    item_verdict_selector,
    mo,
    selected_item,
    selected_ppn,
    selected_row_id,
    set_log,
    timezone,
):
    mo.stop(not item_save_btn.value)
    mo.stop(not selected_item, mo.callout(mo.md("⚠️ Kein Exemplar ausgewählt"), kind="warn"))
    mo.stop(
            item_verdict_selector.value is None,
            mo.callout(mo.md("⚠️ Bitte ein Urteil auswählen, bevor gespeichert wird."), kind="warn"),
        )
    _event = {
        "row_id": selected_row_id,
        "step": "judgment_item",
        "ppn": selected_ppn,
        "epn": selected_item["epn"],
        "shelfmark": selected_item["shelfmark"],
        "judged_by": "human",
        "verdict": item_verdict_selector.value,
        "note": item_note_input.value or None,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    set_log(lambda events: events + [_event])
    mo.md(f"✅ EPN `{selected_item['epn']}` · {selected_item['shelfmark']} → **{item_verdict_selector.value}** (Zeile {selected_row_id})")
    return


@app.cell
def _(datetime, get_log, json, mo, timezone):
    _content = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in get_log())
    mo.vstack([
        mo.md("## Log herunterladen"),
        mo.md(f"*{len(get_log())} Einträge*"),
        mo.download(
            data=_content.encode("utf-8"),
            filename=f"review_{datetime.now(timezone.utc).isoformat()}.jsonl",
            mimetype="application/jsonl",
            label="⬇️ Log herunterladen",
        ),
    ])
    return


@app.cell
def _(mo):
    reset_btn = mo.ui.run_button(label="Log zurücksetzen", kind="danger")
    reset_btn
    return (reset_btn,)


@app.cell
def _(mo, reset_btn, selected_row_id, set_log):
    _reset = selected_row_id  # forces re-run when row changes
    mo.stop(not reset_btn.value)
    set_log([])
    mo.md("🗑️ Log zurückgesetzt")
    return


@app.cell
def _(anywidget, mo):
    class UnsavedChangesGuard(anywidget.AnyWidget):

        _esm = """
        function render({ el }) {
            function actuallyArm() {
                if (window.__unsavedGuardArmed) return;
                window.__unsavedGuardArmed = true;
                window.addEventListener('beforeunload', function (e) {
                    e.preventDefault();
                    e.returnValue = '';
                });
                window.removeEventListener('click', actuallyArm);
                window.removeEventListener('keydown', actuallyArm);
            }
            window.addEventListener('click', actuallyArm);
            window.addEventListener('keydown', actuallyArm);
            el.style.display = "none";
        }
        export default { render };
        """
    guard = mo.ui.anywidget(UnsavedChangesGuard())
    guard
    return


@app.cell
def _(
    all_events: list[dict],
    defaultdict,
    df,
    judgments_by_row_ppn,
    latest_ranking,
    mo,
    pd,
    searches_by_row: dict[str, list[dict]],
):
    _row_ids = [str(r) for r in df["Lfd. Nr."]]
    _n = len(_row_ids)

    def _pct_of(x, base):
        return f"{100 * x / base:.1f}%" if base else "–"


    # 1) Titel gefunden vs. keine gefunden -------------------------------
    # "gefunden" verlangt zusätzlich, dass der beste Kandidat als plausibel
    # eingestuft wurde (n_results <=  expected + tolerance). Bei Retry-Erfolgen fehlt der "plausible"-Key
    # ganz (retry.py loggt ihn nicht) -- solche Zeilen sollen trotzdem
    # zählen, daher "is not False" statt "is True".

    _ok_rows = {rid for rid in _row_ids if latest_ranking.get(rid, {}).get("status") == "ok"}
    _found_rows = {
        rid for rid in _ok_rows
        if latest_ranking.get(rid, {}).get("plausible") is not False
    }

    _found_implausible_rows = _ok_rows - _found_rows
    _none_found_rows = set(_row_ids) - _ok_rows


    _found_ppns = {
        (rid, ppn)
        for rid in _found_rows
        for ppn in (latest_ranking.get(rid, {}).get("ppns") or [])
    }


    # 2) davon nur via Retry-Logik gefunden -------------------------------

    _retry_only_rows = {
        rid for rid in _found_rows
        if (latest_ranking.get(rid, {}).get("chosen_query_name") or "").startswith("llm_retry")
    }

    _retry_only_ppns = {
        (rid, ppn)
        for rid in _retry_only_rows
        for ppn in (latest_ranking.get(rid, {}).get("ppns") or [])
    }


    # --- gemeinsame Grundlage: alle judgment-Events gruppiert nach
    #     (row_id, ppn), + letztes Urteil je Quelle ---------------------------

    events_by_pair: dict[tuple, list] = defaultdict(list)
    for _e in all_events:
        if _e.get("step") == "judgment" and _e.get("ppn"):
            events_by_pair[(_e["row_id"], _e["ppn"])].append(_e)


    last_by_source_by_pair: dict[tuple, dict] = {}
    for _pair, _evs in events_by_pair.items():
        _last = {}
        for _e in sorted(_evs, key=lambda e: e.get("ts", "")):
            _last[_e.get("judged_by", "?")] = _e.get("verdict")
        last_by_source_by_pair[_pair] = _last


    # 3) gefundene Titel, vom LLM als "accept" bewertet --------------------
    _llm_accept_rows = {
        e["row_id"] for e in all_events
        if e.get("step") == "judgment" and e.get("judged_by") == "llm" and e.get("verdict") == "accept"
    } & _found_rows

    _llm_accept_ppns = {
        pair for pair, last in last_by_source_by_pair.items()
        if last.get("llm") == "accept" and pair[0] in _found_rows
    }

    _llm_judged_ppns_in_found = {
        pair for pair, last in last_by_source_by_pair.items()
        if "llm" in last and pair[0] in _found_rows
    }


    # 4) nur durch Menschen gefunden (PPN nicht in Suchergebnissen) --------
    _search_ppns_by_row = {
        rid: {p for s in searches for p in s.get("ppns", [])}
        for rid, searches in searches_by_row.items()
    }

    human_only_ppns = {
        (rid, ppn) for (rid, ppn), j in judgments_by_row_ppn.items()
        if j.get("verdict") == "accept"
        and j.get("judged_by") == "human"
        and ppn not in _search_ppns_by_row.get(rid, set())
    }

    _human_only_rows = {rid for (rid, ppn) in human_only_ppns}


    # 5) abweichende Urteile Mensch vs. LLM ---------------------------------
    # Nur PPNs, die BEIDE Quellen bewertet haben. Fehlendes menschliches
    # Urteil zählt hier bewusst NICHT als Abweichung (siehe Abschnitt 7).

    _reviewed_ppns = {
        pair for pair, last in last_by_source_by_pair.items()
        if "llm" in last and "human" in last
    }

    _disagree_ppns = {
        pair for pair in _reviewed_ppns
        if last_by_source_by_pair[pair]["llm"] != last_by_source_by_pair[pair]["human"]
    }

    _disagree_rows = {pair[0] for pair in _disagree_ppns}

    _reviewed_rows = {
        e["row_id"] for e in all_events
        if e.get("step") == "judgment" and e.get("judged_by") == "human"
    }


    # 5b) laxere Urteile LLM vs. Mensch --------------------------------------

    _disagree_ppns_llm_accept = {
        pair for pair in _reviewed_ppns
        if last_by_source_by_pair[pair]["llm"] == "accept"
        and last_by_source_by_pair[pair]["human"] != "accept"
    }

    _disagree_rows_llm_accept = {pair[0] for pair in _disagree_ppns_llm_accept}


    # 6) Zeilen, für die weder Suche noch LLM noch Mensch etwas gefunden haben ---

    _accepted_rows = {
        pair[0] for pair, last in last_by_source_by_pair.items()
        if "accept" in last.values()
    } | _human_only_rows

    _nothing_found_rows = set(_row_ids) - _found_rows - _accepted_rows


    # 7) Separat: PPNs mit LLM-Urteil, aber ohne menschliches Urteil ---------
    # Fließt NICHT in die Statistik oben ein, nur in die Tabelle unten.

    _no_human_ppns = {
        pair for pair, last in last_by_source_by_pair.items()
        if "llm" in last and "human" not in last
    }

    _row_order = {rid: i for i, rid in enumerate(_row_ids)}

    _missing_human_df = pd.DataFrame(
        [
            {
                "Lfd. Nr.": rid,
                "PPN": ppn,
                "LLM-Urteil": last_by_source_by_pair[(rid, ppn)]["llm"],
                "Titel gefunden (plausibel)": rid in _found_rows,
                "Zeile hat sonst menschl. Urteil": rid in _reviewed_rows,
            }
            for (rid, ppn) in sorted(
                _no_human_ppns,
                key=lambda p: (_row_order.get(p[0], len(_row_order)), p[1]),
            )
        ],
        columns=[
            "Lfd. Nr.",
            "PPN",
            "LLM-Urteil",
            "Titel gefunden (plausibel)",
            "Zeile hat sonst menschl. Urteil",
        ],
    )


    _stats_md = mo.md(f"""

    ## Statistik
    |  | Zeilen | Anteil (Zeilen) | PPNs | Anteil (PPNs) |
    |---|---:|---:|---:|---:|
    | Titel gefunden (plausible Menge) | {len(_found_rows)} | {_pct_of(len(_found_rows), _n)} | {len(_found_ppns)} | – |
    | davon nur via Retry-Logik gefunden | {len(_retry_only_rows)} | {_pct_of(len(_retry_only_rows), _n)} | {len(_retry_only_ppns)} | – |
    | kein Titel gefunden (autom. Suche) | {len(_none_found_rows)} | {_pct_of(len(_none_found_rows), _n)} | – | – |
    | nur durch Mensch gefunden (PPN ∉ Suchergebnisse) | {len(_human_only_rows)} | {_pct_of(len(_human_only_rows), len(_reviewed_rows))} | {len(human_only_ppns)} | – |
    | kein akzeptierter Treffer (weder LLM noch Mensch) | {len(_nothing_found_rows)} | {_pct_of(len(_nothing_found_rows), _n)} | – | – |
    | gefundene Titel von LLM als „accept" bewertet | {len(_llm_accept_rows)} | {_pct_of(len(_llm_accept_rows), _n)} | {len(_llm_accept_ppns)} | {_pct_of(len(_llm_accept_ppns), len(_llm_judged_ppns_in_found))} |
    | Urteil Mensch ≠ LLM | {len(_disagree_rows)} | {_pct_of(len(_disagree_rows), _n)} | {len(_disagree_ppns)} | {_pct_of(len(_disagree_ppns), len(_reviewed_ppns))} |
    | Urteil LLM "accept"; Mensch "uncertain / reject" | {len(_disagree_rows_llm_accept)} | {_pct_of(len(_disagree_rows_llm_accept), _n)} | {len(_disagree_ppns_llm_accept)} | {_pct_of(len(_disagree_ppns_llm_accept), len(_reviewed_ppns))} |


    *Zeilen-Basis: {_n} Zeilen aus der CSV*

    """)

    mo.vstack([
        _stats_md,
        mo.md(f"### PPNs ohne menschliches Urteil ({len(_missing_human_df)})"),
        mo.ui.table(_missing_human_df, selection=None),
    ])
    return events_by_pair, human_only_ppns, last_by_source_by_pair


@app.cell
def _(
    df,
    events_by_pair: dict[tuple, list],
    last_by_source_by_pair: dict[tuple, dict],
    mo,
    pd,
):
    def _latest_event(pair, source):
        _evs = [e for e in events_by_pair[pair] if e.get("judged_by") == source]
        return max(_evs, key=lambda e: e.get("ts", "")) if _evs else {}

    _records = []

    for _pair, _last in last_by_source_by_pair.items():
        if "llm" in _last and "human" in _last and _last["llm"] != _last["human"]:
            _h = _latest_event(_pair, "human")
            _l = _latest_event(_pair, "llm")
            _records.append({
                "Lfd. Nr.": _pair[0],
                "PPN": _pair[1],
                "Urteil Mensch": _last["human"],
                "Urteil LLM": _last["llm"],
                "Konfidenz LLM": _l.get("confidence"),
                "Notiz Mensch": _h.get("note"),
                "Begründung LLM": _l.get("reasoning"),
            })


    disagree_df = (
        pd.DataFrame(_records)
        .merge(df[["Lfd. Nr.", "Titel"]], on="Lfd. Nr.", how="left")
        .sort_values("Lfd. Nr.", key=lambda s: s.astype(int))
        .reset_index(drop=True)
    )

    disagree_df_llm_accept = disagree_df[(disagree_df["Urteil LLM"] == "accept") & (disagree_df["Urteil Mensch"] != "accept")
    ].copy()
    mo.vstack([

        mo.md(f"### Urteil Mensch ≠ LLM · {disagree_df['Lfd. Nr.'].nunique()} Zeilen / {len(disagree_df)} PPNs"),

        mo.ui.table(disagree_df, selection=None),

        mo.md(f"### Urteil LLM = accept vs. Urteil Mensch = reject / uncertain · {disagree_df_llm_accept['Lfd. Nr.'].nunique()} Zeilen / {len(disagree_df_llm_accept)} PPNs"),

        mo.ui.table(disagree_df_llm_accept, selection=None)

    ])
    return


@app.cell
def _(
    all_events: list[dict],
    df,
    human_only_ppns,
    judgments_by_row_ppn,
    mo,
    pd,
):
    # latest item-level (EPN) judgment per (row_id, ppn, epn)
    _items: dict[tuple, dict] = {}
    for _e in all_events:
        if _e.get("step") != "judgment_item":
            continue
        _k = (_e["row_id"], _e.get("ppn"), _e.get("epn"))
        if _k not in _items or _e.get("ts", "") > _items[_k].get("ts", ""):
            _items[_k] = _e

    def _shelfmarks(row_id, ppn):
        return ", ".join(
            f"{e.get('shelfmark', '—')} ({e.get('verdict')})"
            for (r, p, _), e in _items.items() if r == row_id and p == ppn
        ) or None

    _records = []
    for _row_id, _ppn in human_only_ppns:
        _j = judgments_by_row_ppn[(_row_id, _ppn)]
        _records.append({
            "Lfd. Nr.": _row_id,
            "PPN": _ppn,
            "Notiz": _j.get("note"),

        })

    human_only_df = (
        pd.DataFrame(_records,
                     columns=["Lfd. Nr.", "PPN", "Notiz"])
        .merge(df[["Lfd. Nr.", "Titel"]], on="Lfd. Nr.", how="left")
        .sort_values(["Lfd. Nr.", "PPN"], key=lambda s: s.astype(str).str.zfill(12))
        .reset_index(drop=True)
    )

    mo.vstack([
        mo.md(f"### Nur durch manuell angepasste Suche gefunden · "
              f"{human_only_df['Lfd. Nr.'].nunique()} Zeilen / {len(human_only_df)} PPNs"),
        mo.ui.table(human_only_df, selection=None),
    ])
    return


@app.cell
def _(mo):
    mo.md("""
    ### Mehr Statistik: Akzeptierte PPNs enthalten
    """)
    return


@app.cell
def _(mo):
    run_statistics = mo.ui.run_button(label="Records abfragen, um Statistik zu erzeugen; 1 SRU-Abfrage/PPN")
    run_statistics
    return (run_statistics,)


@app.cell
def _(
    human_only_ppns,
    last_by_source_by_pair: dict[tuple, dict],
    mo,
    run_statistics,
    urllib,
):
    mo.stop(not run_statistics.value)
    _SRU_URL = "https://sru.k10plus.de/opac-de-1"  # wie im Notebook (stabikat)

    # Akzeptierte PPNs (LLM oder Mensch, letztes Urteil)
    sru_accepted = {}  # ppn -> {"sources": set, "rows": set}

    for (_rid, _ppn), _last in last_by_source_by_pair.items():
        for _src, _verdict in _last.items():
            if _verdict == "accept":
                _e = sru_accepted.setdefault(_ppn, {"sources": set(), "rows": set()})
                _e["sources"].add(_src)
                _e["rows"].add(_rid)

    for _rid, _ppn in human_only_ppns:
        _e = sru_accepted.setdefault(_ppn, {"sources": set(), "rows": set()})
        _e["sources"].add("human")
        _e["rows"].add(_rid)

    # Records abrufen
    sru_raw = {}     # ppn -> XML-String
    sru_errors = {}  # ppn -> Fehlermeldung

    for _p in mo.status.progress_bar(sorted(sru_accepted), title="SRU-Abfragen (picaxml)"):
        _params = urllib.parse.urlencode({
            "version": "1.1",
            "operation": "searchRetrieve",
            "recordSchema": "picaxml",
            "maximumRecords": "1",
            "query": f"pica.xppn={_p}",
        })
        try:
            with urllib.request.urlopen(f"{_SRU_URL}?{_params}", timeout=30) as _resp:
                sru_raw[_p] = _resp.read().decode("utf-8")
        except Exception as _exc:
            sru_errors[_p] = f"{type(_exc).__name__}: {_exc}"

    mo.md(
        f"SRU: {len(sru_accepted)} akzeptierte PPNs · {len(sru_raw)} abgerufen · "
        f"**{len(sru_errors)} Fehler**"
    )
    return sru_accepted, sru_errors, sru_raw


@app.cell
def _(ET, mo, pd, sru_accepted, sru_errors, sru_raw):
    def _pct(x, base):
        return f"{100 * x / base:.1f}%" if base else "–"


    def _parse(ppn):
        if ppn not in sru_raw:
            return {"status": "error", "error": sru_errors.get(ppn, "nicht abgerufen")}
        _root = ET.fromstring(sru_raw[ppn])
        if int(_root.findtext("{*}numberOfRecords") or 0) == 0:
            return {"status": "not_found", "error": ""}

        _f209a = _root.findall(".//{*}datafield[@tag='209A']")
        _f_values = [
            (_sf.text or "").strip()
            for _fld in _f209a
            if _fld.get("occurrence") == "01"
            for _sf in _fld.findall("{*}subfield[@code='f']")
        ]

         # 039D mit $c oder $i beginnend mit "Digital" (z. B. "Digitalisierte Ausg.")
        _digi = any(
            (_sf.text or "").strip().startswith("Digital")
            for _fld in _root.findall(".//{*}datafield[@tag='039D']")
            for _sf in _fld.findall("{*}subfield")
            if _sf.get("code") in ("c", "i")
        )

        return {
            "status": "ok",
            "error": "",
            "n_209a": len(_f209a),
            "has_01": any(_fld.get("occurrence") == "01" for _fld in _f209a),
            "f_values": _f_values,
            "f4": any(_v.startswith("4") for _v in _f_values),
            "digi": _digi,
        }


    _parsed = {_p: _parse(_p) for _p in sorted(sru_accepted)}

    sru_records_df = pd.DataFrame([
        {
            "PPN": _p,
            "Zeilen (Lfd. Nr.)": ", ".join(sorted(sru_accepted[_p]["rows"], key=lambda r: (len(r), r))),
            "accept von": " + ".join(sorted(sru_accepted[_p]["sources"])),
            "Status": _r["status"],
            "Anzahl 209A": _r.get("n_209a"),
            "209A/01 vorhanden": _r.get("has_01"),
            "209A/01 $f": ", ".join(_r.get("f_values", [])),
            "$f beginnt mit 4": _r.get("f4"),
            "mehrere 209A": (_r["n_209a"] > 1) if _r["status"] == "ok" else None,
            "hat digitalisierte Version": _r.get("digi"),
            "Fehler": _r["error"],
        }
        for _p, _r in _parsed.items()
    ])
    _problems_df = sru_records_df[sru_records_df["Status"] != "ok"]

    _ok = [_r for _r in _parsed.values() if _r["status"] == "ok"]
    _n_acc, _n_ok = len(_parsed), len(_ok)
    _n_nf = sum(_r["status"] == "not_found" for _r in _parsed.values())
    _n_err = sum(_r["status"] == "error" for _r in _parsed.values())
    _n_any = sum(_r["n_209a"] > 0 for _r in _ok)
    _n_01 = sum(_r["has_01"] for _r in _ok)
    _n_f4 = sum(_r["f4"] for _r in _ok)
    _n_multi = sum(_r["n_209a"] > 1 for _r in _ok)
    _n_digi = sum(_r["digi"] for _r in _ok)

    mo.vstack([
        mo.md(f"""

    ## Statistik: 209A in akzeptierten Records
    |  | PPNs | Anteil |
    |---|---:|---:|
    | Akzeptierte PPNs (LLM oder Mensch, eindeutig) | {_n_acc} | – |
    | Record abgerufen | {_n_ok} | {_pct(_n_ok, _n_acc)} |
    | nicht gefunden | {_n_nf} | {_pct(_n_nf, _n_acc)} |
    | Abruf-Fehler / nicht abgerufen | {_n_err} | {_pct(_n_err, _n_acc)} |
    | Record hat mind. ein Feld 209A | {_n_any} | {_pct(_n_any, _n_ok)} |
    | Record hat 209A/01 | {_n_01} | {_pct(_n_01, _n_ok)} |
    | 209A/01 $f beginnt mit „4" | {_n_f4} | {_pct(_n_f4, _n_ok)} |
    | mehrere Felder 209A | {_n_multi} | {_pct(_n_multi, _n_ok)} |
    | hat digitalisierte Version (039D $c „Digital…") | {_n_digi} | {_pct(_n_digi, _n_ok)} |

    *Basis der Anteile: abgerufene Records.*

    """),
        mo.md("### Records"),
        mo.ui.table(sru_records_df, selection=None),
        *([mo.md(f"### Nicht abgerufen / nicht gefunden ({len(_problems_df)})"),
           mo.ui.table(_problems_df, selection=None)] if len(_problems_df) else []),
    ])
    return


if __name__ == "__main__":
    app.run()
