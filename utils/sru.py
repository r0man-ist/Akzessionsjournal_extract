from __future__ import annotations
from urllib.parse import urlencode

import pandas as pd
import ast
import requests
import re
from lxml import etree

SRU_BASE_URLS = {
    "stabikat": "https://sru.k10plus.de/opac-de-1",
    "k10plus": "https://sru.k10plus.de/opac-de-627",
    "VD17": "https://sru.k10plus.de/vd17",
}

DEFAULT_RECORD_SCHEMA = "marcxml"

NS = {
    "marc": "http://www.loc.gov/MARC21/slim",
    "zs": "http://www.loc.gov/zing/srw/",
    "ppxml": "http://www.oclcpica.org/xmlns/ppxml-1.0",
}


def remove_ellipses(value: str) -> str:
    value = value.replace("[...]", "")
    value = value.replace("[", "")
    value = value.replace("]", "")
    return value


def replace_slash(value: str) -> str:
    return value.replace("/", " ")


def quote(value: str) -> str:
    needs_quotes = any(ch.isspace() for ch in value) or any(ch in '<>=/()' for ch in value)
    return f'"{value}"' if needs_quotes else value


def prepare_cql_string(value) -> str:
    """Sanitise + quote a single value for safe inclusion in a CQL query."""
    if value is None or pd.isna(value):
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = remove_ellipses(value)
    value = replace_slash(value)
    value = quote(value)
    return value


def query_sru(query: str, catalogue: str, maximum_records: int = 20, timeout: int = 30) -> str:
    if catalogue not in SRU_BASE_URLS:
        raise ValueError(f"Unknown catalogue '{catalogue}', expected one of {list(SRU_BASE_URLS)}")
    base_url = SRU_BASE_URLS[catalogue]

    if catalogue == "stabikat":
        query = query.replace("pica.", "pica.x")

    params = {
        "recordSchema": DEFAULT_RECORD_SCHEMA,
        "operation": "searchRetrieve",
        "version": "1.1",
        "maximumRecords": str(maximum_records),
        "query": query,
    }
    query_string = urlencode(params, safe="+")
    print(f"Sending request to {base_url}?{query_string}") # for debugging purposes
    response = requests.get(f"{base_url}?{query_string}", timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_sru(xml_string: str) -> tuple[int, list[str]]:
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


def run_query(query: str, catalogue: str, exclude_digitised: bool = True,
              maximum_records: int = 20) -> tuple[int, list[str]]:
    """Run a ready-made CQL query string and parse the response."""
    if not query.strip():
        return 0, []
    if exclude_digitised:
        query = f"{query} NOT pica.bbg=O*"
    print(f"Running query: {query}") # for debugging purposes
    xml = query_sru(query, catalogue, maximum_records=maximum_records)
    print(f"Received XML: {xml[:800]}...") # for debugging purposes
    return parse_sru(xml)


def build_year_or_clause(years: list[int], index: str = "pica.jah") -> str:
    """
    Build a CQL fragment OR-ing a list of already-parsed years, e.g. from normalize_years:
      [1900]            -> "pica.jah=1900"
      [1888, 1889]       -> "(pica.jah=1888 OR pica.jah=1889)"
      []                 -> ""  (signals "skip" upstream)
    """
    if not years:
        return ""
    if len(years) == 1:
        return f"{index}={years[0]}"
    clauses = " OR ".join(f"{index}={y}" for y in years)
    return f"({clauses})"


def get_record(ppn: str, catalogue: str = "stabikat") -> str:
    """Retrieve a single SRU record as MARCXML."""
    query = f"pica.ppn={ppn}"
    return query_sru(
        query,
        catalogue,
        maximum_records=1,
    )