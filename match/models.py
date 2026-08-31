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
    failure_reason: str = Field(max_length=150, description="One short sentence on why the previous queries likely failed.")
    proposed_query: str = Field(description="A complete, ready-to-run CQL query using only pica.tit, pica.jah, and pica.per fields.")
    reasoning: str = Field(max_length=150, description="One short sentence on why this new query should work better.")