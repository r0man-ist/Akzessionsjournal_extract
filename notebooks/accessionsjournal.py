import marimo

__generated_with = "0.21.1"
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
    searches_by_row: dict[str, list[dict]],
):
    _row_ids = [str(r) for r in df["Lfd. Nr."]]
    _n = len(_row_ids)

    def _pct_of(x, base):
        return f"{100 * x / base:.1f}%" if base else "–"


    # 1) Titel gefunden vs. keine gefunden -------------------------------

    # "gefunden" verlangt zusätzlich, dass der beste Kandidat als plausibel

    # eingestuft wurde (rank.py: plausible = n_results > 0 and n_results <=

    # expected * tolerance). Bei Retry-Erfolgen fehlt der "plausible"-Key

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

    _found_implausible_ppns = {
        (rid, ppn)
        for rid in _found_implausible_rows
        for ppn in (latest_ranking.get(rid, {}).get("ppns") or [])
    }


    # 2) davon nur via Retry-Logik gefunden -------------------------------

    _retry_only_rows = {
        rid for rid in _found_rows
        if latest_ranking.get(rid, {}).get("chosen_query_name") == "llm_retry"
    }

    _retry_only_ppns = {
        (rid, ppn)
        for rid in _retry_only_rows
        for ppn in (latest_ranking.get(rid, {}).get("ppns") or [])

    }


    # --- gemeinsame Grundlage für 3) und 5): alle judgment-Events
    #     gruppiert nach (row_id, ppn), + letztes Urteil je Quelle ---------

    _events_by_pair: dict[tuple, list] = defaultdict(list)
    for _e in all_events:
        if _e.get("step") == "judgment" and _e.get("ppn"):
            _events_by_pair[(_e["row_id"], _e["ppn"])].append(_e)


    _last_by_source_by_pair: dict[tuple, dict] = {}
    for _pair, _evs in _events_by_pair.items():
        _last = {}
        for _e in sorted(_evs, key=lambda e: e.get("ts", "")):
            _last[_e.get("judged_by", "?")] = _e.get("verdict")
        _last_by_source_by_pair[_pair] = _last


    # 3) gefundene Titel, vom LLM als "accept" bewertet --------------------
    _llm_accept_rows = {
        e["row_id"] for e in all_events
        if e.get("step") == "judgment" and e.get("judged_by") == "llm" and e.get("verdict") == "accept"
    } & _found_rows


    _llm_accept_ppns = {
        pair for pair, last in _last_by_source_by_pair.items()
        if last.get("llm") == "accept" and pair[0] in _found_rows
    }

    _llm_judged_ppns_in_found = {
        pair for pair, last in _last_by_source_by_pair.items()
        if "llm" in last and pair[0] in _found_rows
    }


    # 4) nur durch Menschen gefunden (PPN nicht in Suchergebnissen) --------
    _search_ppns_by_row = {
        rid: {p for s in searches for p in s.get("ppns", [])}
        for rid, searches in searches_by_row.items()
    }

    _human_only_ppns = {
        (rid, ppn) for (rid, ppn), j in judgments_by_row_ppn.items()
        if j.get("verdict") == "accept"
        and j.get("judged_by") == "human"
        and ppn not in _search_ppns_by_row.get(rid, set())
    }

    _human_only_rows = {rid for (rid, ppn) in _human_only_ppns}


    # 5) abweichende Urteile Mensch vs. LLM ---------------------------------

    _disagree_rows = {
        pair[0] for pair, last in _last_by_source_by_pair.items()
        if "llm" in last and "human" in last and last["llm"] != last["human"]
    }

    _disagree_ppns = {
        pair for pair, last in _last_by_source_by_pair.items()
        if "llm" in last and "human" in last and last["llm"] != last["human"]
    }

    _reviewed_ppns = {
        pair for pair, last in _last_by_source_by_pair.items()
        if "llm" in last and "human" in last
    }

    _reviewed_rows = {
        e["row_id"] for e in all_events
        if e.get("step") == "judgment" and e.get("judged_by") == "human"
    }


    mo.md(f"""

    ## Statistik
    | Kennzahl | Zeilen | Anteil (Zeilen) | PPNs | Anteil (PPNs) |
    |---|---:|---:|---:|---:|
    | Titel gefunden (plausibel) | {len(_found_rows)} | {_pct_of(len(_found_rows), _n)} | {len(_found_ppns)} | – |
    | gefunden, aber unplausibel (z. B. zu viele Treffer) | {len(_found_implausible_rows)} | {_pct_of(len(_found_implausible_rows), _n)} | {len(_found_implausible_ppns)} | – |
    | kein Titel gefunden | {len(_none_found_rows)} | {_pct_of(len(_none_found_rows), _n)} | – | – |
    | davon nur via Retry-Logik gefunden | {len(_retry_only_rows)} | {_pct_of(len(_retry_only_rows), _n)} | {len(_retry_only_ppns)} | – |
    | gefundene Titel von LLM als „accept" bewertet | {len(_llm_accept_rows)} | {_pct_of(len(_llm_accept_rows), _n)} | {len(_llm_accept_ppns)} | {_pct_of(len(_llm_accept_ppns), len(_llm_judged_ppns_in_found))} || nur durch Mensch gefunden (PPN ∉ Suchergebnisse) | {len(_human_only_rows)} | {_pct_of(len(_human_only_rows), len(_reviewed_rows))} | {len(_human_only_ppns)} | – |
    | Urteil Mensch ≠ LLM | {len(_disagree_rows)} | {_pct_of(len(_disagree_rows), _n)} | {len(_disagree_ppns)} | {_pct_of(len(_disagree_ppns), len(_found_ppns))} |
    | Nur durch manuell angepasste Suche gefunden (zusätzlich, PPN ∉ Suchergebnisse) | {len(_human_only_rows)} | {_pct_of(len(_human_only_rows), _n)} | {len(_human_only_ppns)} | – |
    *Zeilen-Basis: {_n} Zeilen aus der CSV · {len(_reviewed_rows)} davon mit mind. einem menschl. Urteil.*

    """)
    return


if __name__ == "__main__":
    app.run()
