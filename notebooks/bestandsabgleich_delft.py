import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    from urllib.parse import urlencode, unquote
    import requests
    from lxml import etree
    import re
    import ast

    return ast, etree, io, mo, pd, requests, urlencode


@app.cell
def _(mo):
    mo.md("""
    # Provenienzerschließung für Akzessionsjournale
    """)
    return


@app.cell
def _(mo):
    upload = mo.ui.file(filetypes=[".csv"], kind="area", label="CSV-Datei laden")
    mo.vstack([mo.md("""## CSV-Datei hochladen
    Laden Sie eine csv-Datei hoch. Diese muss die bibliographischen Angaben aus dem Akzessionsjournal enthalten **und** auch bereits abgeglichene Treffer"""), upload])
    return (upload,)


@app.cell
def _(io, mo, pd, upload):
    uploaded_file = upload.value[0]  # single-file upload
    df = pd.read_csv(
        io.BytesIO(uploaded_file.contents),
        sep=";",
        encoding="utf-8"
    )
    input_table = mo.ui.table(df, selection="single")
    mo.vstack([input_table, mo.md("""### Wählen sie aus der Tabelle eine Zeile""")])
    return df, input_table


@app.cell
def _(input_table, mo):
    selected_row = input_table.value
    row = selected_row.iloc[0]
    mo.vstack([
        mo.md(f"**{col}:** {value}")
        for col, value in row.iloc[:6].items()
    ])
    return row, selected_row


@app.cell
def _(df, pd, row):
    treffer_cols = [c for c in df.columns if c.startswith("Treffer")]
    zahl = pd.to_numeric(row["Zahl"], errors="coerce")

    def diff_key(col):
        val = pd.to_numeric(row[col], errors="coerce")
        if pd.isna(val) or pd.isna(zahl) or val == 0:
            return (float("inf"), 1)
        d = val - zahl
        return (abs(d), 0 if d >= 0 else 1)

    closest_col = min(treffer_cols, key=diff_key)
    return (closest_col,)


@app.cell
def _(closest_col, mo):
    get_selected, set_selected = mo.state(closest_col)
    return


@app.cell
def _(closest_col, mo, row):
    option_labels = {
        f"Titel + Autor + Jahr  ·  {row['Treffer_title_search_author_normalized_Jahr_CQL']} Treffer":
            "Treffer_title_search_author_normalized_Jahr_CQL",

        f"Titel + Author  ·  {row['Treffer_title_search_author_normalized']} Treffer":
            "Treffer_title_search_author_normalized",

        f"Titel  ·  {row['Treffer_title_search']} Treffer":
            "Treffer_title_search",
    }


    selected = mo.ui.radio(
        options=option_labels,
        value=next(
            label for label, col in option_labels.items()
            if col == closest_col
        ),
        inline=True,
        label="Treffer gefunden:  ",
    )


    mo.vstack([mo.md(f"""
    **{int(row["Zahl"])} Bände erwartet**
    """), selected])
    return (selected,)


@app.cell
def _(selected):
    chosen_col = selected.value
    return (chosen_col,)


@app.cell
def _(ast, chosen_col, row):
    PPN_selected = ast.literal_eval(row[chosen_col.replace("Treffer", "PPN")])
    return (PPN_selected,)


@app.cell
def _(PPN_selected, mo):
    mo.md(f"""
    Mit der gewählten Suchanfrage wurden {len(PPN_selected)} Treffer gefunden mit den PPNs {PPN_selected}
    """)
    return


@app.cell
def _(PPN_selected, mo):
    max_index = len(PPN_selected) - 1
    button = mo.ui.button(
        value=0, on_click=lambda value: (value + 1) % len(PPN_selected), label="Nächste PPN", kind="warn"
    )
    button
    return (button,)


@app.cell
def _(PPN_selected, button):
    try: 
        selected_PPN = PPN_selected[button.value]
    except:
        selected_PPN = None
    return (selected_PPN,)


@app.cell
def _(df):
    df["PPN_geprueft"] = [[] for _ in range(len(df))]
    return


@app.cell
def _(PPN_selected, button, df, mo, row):
    get_message, set_message = mo.state("")

    def save_selected_ppn(_):
        ppn = PPN_selected[button.value]
        current = df.at[row.name, "PPN_geprueft"]

        if ppn not in current:
            current.append(ppn)
            set_message(f"✅ PPN {ppn} gespeichert")
        else:
            set_message(f"⚠️ PPN {ppn} bereits ausgewählt")

    save_button = mo.ui.button(
        label="PPN speichern",
        kind="success",
        on_click=save_selected_ppn,
    )


    save_button
    return get_message, save_button


@app.cell
def _(get_message, mo):
    mo.md(get_message())
    return


@app.cell
def _(PPN_selected, button, df, row_idx, save_button):
    if save_button.value:
        df.at[row_idx, "chosen_ppn"] = PPN_selected[button.value]
    return


@app.cell
def _(mo, selected_PPN):
    stabikat_url = f"https://stabikat.de/Search/Results?lookfor=id%3A{selected_PPN}&type=AllFields" if selected_PPN else f"https://stabikat.de/"
    mo.iframe(stabikat_url, height=600)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Exemplardaten
    """)
    return


@app.cell
def _(df, input_table):
    selected_row_ppn = df[
        df["Lfd. Nr."] == input_table.value["Lfd. Nr."].iloc[0]
    ].iloc[0]
    return (selected_row_ppn,)


@app.cell
def _(selected_row_ppn):
    selected_row_ppn["PPN_geprueft"]
    return


@app.cell
def _(mo):
    mo.md("""
    TODO
    - for PPN in selected_row_ppn:
     - query_sru
     - extract Item information
     - list EPN and shelfmark
     - check if there are 361-fields!

     - write epns and signature to df

    - add row: correct & done
    """)
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    mo.md("""
    ## Neue Suche ausführen
    """)
    return


@app.cell
def _():
    # Constants
    # SRU base URLs
    SBB_SRU_BASE = "https://sru.k10plus.de/opac-de-1"
    k10plus_SRU_BASE = "https://sru.k10plus.de/opac-de-627"
    VD17_SRU_BASE = "https://sru.k10plus.de/vd17"

    # Default SRU parameters
    DEFAULT_RECORD_SCHEMA = "marcxml"

    # XML Namespaces
    NS = {
    "marc": "http://www.loc.gov/MARC21/slim",
    "zs": "http://www.loc.gov/zing/srw/",
    "ppxml": "http://www.oclcpica.org/xmlns/ppxml-1.0"
    }
    return (
        DEFAULT_RECORD_SCHEMA,
        NS,
        SBB_SRU_BASE,
        VD17_SRU_BASE,
        k10plus_SRU_BASE,
    )


@app.cell
def _(
    DEFAULT_RECORD_SCHEMA,
    SBB_SRU_BASE,
    VD17_SRU_BASE,
    catalogue,
    k10plus_SRU_BASE,
    requests,
    urlencode,
):
    def query_sru(query):
        if catalogue.value == "stabikat":
            base_url = SBB_SRU_BASE
        if catalogue.value == "k10plus":
             base_url = k10plus_SRU_BASE
        if catalogue.value == "VD17":    
             base_url = VD17_SRU_BASE

        #Escape some charaters in the query (but not in the index prefix)
        #pattern = re.compile(r'(?<!pica)\.|\(|\)|<|>|/')

        #query = pattern.sub(lambda m: "\\" + m.group(), query)

        # Add "x" in front of Index-term for stabikat
        if catalogue.value == "stabikat":
           query = query.replace("pica.", "pica.x")

        params = {
            'recordSchema': DEFAULT_RECORD_SCHEMA,
            'operation': 'searchRetrieve',
            'version': '1.1',
            'maximumRecords': '20',
            'query': query
        }

        query_string = urlencode(params, safe="+")
        print(query_string) # for debugging
        response = requests.get(f"{base_url}?{query_string}")
        response.raise_for_status()
        return response.text

    return


@app.cell
def _(NS, etree):
    def parse_sru(xml_string):
        parser = etree.XMLParser(recover=True)

        if isinstance(xml_string, bytes):
            xml_string = xml_string.decode("utf-8", errors="replace")

        root = etree.fromstring(xml_string.encode("utf-8"), parser)

        number_of_records = int(
            root.findtext(".//zs:numberOfRecords", default="0", namespaces=NS) or 0
        )

        ppns = [
            elem.text
            for elem in root.findall('.//marc:controlfield[@tag="001"]', namespaces=NS)
            if elem.text is not None
        ]



        return number_of_records, ppns

    return


@app.cell
def _(mo, selected_row):
    _rows = [
        mo.hstack([mo.md(f"**{col}**"), mo.md(str(selected_row[col]))])
        for col in selected_row.index
    ]
    metadata_view = mo.vstack([mo.md(f"### Zeile {selected_row.name}")] + _rows)
    metadata_view
    return


@app.cell
def _(df_abgleich, mo, ppn_selector, save_ppn_button, selected_idx):
    mo.stop(not save_ppn_button.value)
    if "PPN_correct" not in df_abgleich.columns:
        df_abgleich["PPN_correct"] = ""
    selected_ppn = ppn_selector.value
    if selected_ppn and selected_ppn != "– keine Treffer –":
        current = df_abgleich.at[selected_idx, "PPN_correct"]
        existing_ppns = [
        p.strip() for p in str(current).split(",") if p.strip() and p.strip() != "nan"
        ]
        if selected_ppn not in existing_ppns:
            existing_ppns.append(selected_ppn)
    df_abgleich.at[selected_idx, "PPN_correct"] = ", ".join(existing_ppns)

    mo.md(f"✅ PPN {selected_ppn} für Zeile {selected_idx} gespeichert.")
    return


@app.cell
def _(df_abgleich):
    df_abgleich
    return


if __name__ == "__main__":
    app.run()
