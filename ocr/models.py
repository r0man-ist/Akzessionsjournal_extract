# ocr/models.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class OcrEntry(BaseModel):
    accession_no: str = Field(
        default="",
        description="The leftmost accession number, as written. Empty string if blank.",
    )
    date: str = Field(
        default="",
        description=(
            "Constructed date in the form DAY.[MONTH YEAR], e.g. '4.[Jan.1895]'. "
            "Resolve ditto marks from the nearest preceding explicit day value on this page."
        ),
    )
    letter: str = Field(
        default="",
        description="The letter column, transcribed literally.",
    )
    entry_text: str = Field(
        default="",
        description=(
            "The full bibliographic citation cell, transcribed literally and "
            "ditto-resolved per the general principle: resolve only the part "
            "the ditto mark stands in for, preserving any explicitly written text."
        ),
    )
    source_note: str = Field(
        default="",
        description=(
            "Dealer/source name and date, transcribed literally and ditto-resolved "
            "(e.g. vendor name repeating while date changes)."
        ),
    )
    mark: str = Field(
        default="",
        description="Symbol in the mark column, transcribed literally.",
    )
    price: str = Field(
        default="",
        description="The price figure, transcribed literally.",
    )
    fraction: str = Field(
        default="",
        description="Contents of the fraction column, transcribed literally.",
    )
    subject_group: str = Field(
        default="",
        description="The subject group column, transcribed literally.",
    )
    quantity: str = Field(
        default="",
        description="The quantity/count column, transcribed literally.",
    )
    binding_note: str = Field(
        default="",
        description="Binding remarks such as 'gbd.', '1', etc., transcribed literally.",
    )
    row_confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "Overall certainty reading this row: 'high', 'medium', or 'low'. "
            "Reflects handwriting legibility, ambiguous corrections, and unclear "
            "ditto resolution."
        ),
    )
    unusual_marks: str = Field(
        default="",
        description=(
            "Short literal description of any anomaly in the row, or empty string if none. "
            "Covers cancellations, color/ink additions, marginal notes (transcribed literally), "
            "overwrites, partial ditto ambiguity, and other visible anomalies. "
            "Multiple anomalies separated by semicolons."
        ),
    )


class OcrPage(BaseModel):
    page_number: str = Field(
        default="",
        description=(
            "The page number as printed or handwritten on the page itself "
            "(e.g. from a header or footer). Empty string if not present."
        ),
    )
    is_empty: bool = Field(
        description=(
            "True if the page has no tabular entries (cover, endpaper, title page, "
            "blank page, inserted note, etc.). If True, entries must be an empty list."
        ),
    )
    entries: list[OcrEntry] = Field(
        description="One OcrEntry per accession row on the page, in top-to-bottom order.",
    )