from typing import Literal
from pydantic import BaseModel, Field


class JudgmentResult(BaseModel):
    verdict: Literal["accept", "reject", "uncertain"] = Field(
        description="Whether the candidate record matches the accession entry."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence in the verdict."
    )
    reasoning: str = Field(
        max_length=150,
        description="A single short sentence (max ~20 words) naming the key matching or mismatching field(s).",
    )

class DiagnosisResult(BaseModel):
    failure_reason: str = Field(description="One short sentence on why the previous queries likely failed.")
    proposed_queries: list[str] = Field(
        description="2-3 complete CQL queries, strictest first. Each must use a different "
                    "strategy (e.g. other title words, with/without year, surname only). "
                    "Never repeat a query that was already tried."
    )
    reasoning: str = Field(description="One short sentence on the strategy behind the queries.")