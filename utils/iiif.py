# utils/iiif.py
from __future__ import annotations
import json
import re
from pathlib import Path


def find_manifest(directory: Path) -> Path | None:
    """Return the first IIIF manifest JSON found in directory, or None."""
    candidates = list(directory.glob("*manifest*.json"))
    return candidates[0] if candidates else None


def load_iiif_canvas_map(manifest_path: Path) -> dict[int, str]:
    """
    Parse a IIIF Presentation v2 manifest and return a dict mapping
    canvas position (1-based) to a viewer URL.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    canvases = (manifest.get("sequences") or [{}])[0].get("canvases") or []

    pattern = re.compile(r"/dc/([^/]+?)-(\d+)/canvas")
    result: dict[int, str] = {}
    for i, canvas in enumerate(canvases, start=1):
        m = pattern.search(canvas.get("@id", ""))
        if not m:
            continue
        ppn_base, phys_num = m.group(1), m.group(2)
        result[i] = (
            f"https://digital.staatsbibliothek-berlin.de/werkansicht"
            f"?PPN=PPN{ppn_base}&PHYSID=PHYS_{phys_num}"
        )
    return result