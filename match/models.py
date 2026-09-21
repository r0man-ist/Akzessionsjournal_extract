from typing import Literal
from pydantic import BaseModel, Field


class JudgmentResult(BaseModel):
    matching_fields: list[str] = Field(
        description="Fields identical after the allowed normalizations, e.g. ['title', 'author', 'year', 'place']."
    )
    volume_relation: Literal["same_unit", "volume_of_entry_work", "collective_of_entry_work", "not_applicable"] = Field(
        description="How the record relates to the entry in terms of volumes/parts. "
                    "A record for one volume, or the collective record, of the multivolume work in the entry "
                    "goes here and NEVER into the discrepancy lists."
    )
    minor_discrepancies: list[str] = Field(
        description="Small character-level differences only, each as 'field: entry <X> vs record <Y>'. "
                    "Empty list if none."
    )
    major_discrepancies: list[str] = Field(
        description="All other differences, each as 'field: entry <X> vs record <Y>'. "
                    "Do not explain or excuse them. Empty list if none."
    )
    missing_fields: list[str] = Field(
        description="Fields present on one side only."
    )
    reasoning: str = Field(description="One short sentence naming the decisive field(s).")
    verdict: Literal["accept", "reject", "uncertain"]
    confidence: Literal["high", "medium", "low"]

class DiagnosisResult(BaseModel):
    failure_reason: str = Field(description="One short sentence on why the previous queries likely failed.")
    proposed_queries: list[str] = Field(
        description="2-3 complete CQL queries, strictest first. Each must use a different "
                    "strategy (e.g. other title words, with/without year, surname only). "
                    "Never repeat a query that was already tried."
    )
    reasoning: str = Field(description="One short sentence on the strategy behind the queries.")