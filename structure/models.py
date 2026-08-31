from pydantic import BaseModel, Field

class BibliographicRecord(BaseModel):


    title_raw: str  = Field(
        default="",
        description="The title exactly as it appears in the reference. Empty string if no title can be found.",
    )

    title_normalized: str | None = Field(
        default=None,
        description="The title with abbreviations expanded and minor normalization applied.",
    )

    title_search: str | None = Field(
        default=None,
        description=(
            "An aggressively normalized version of the title optimized for "
            "searching and fuzzy matching."
        ),
    )


    author_raw: list[str] | None = Field(
        default=None,
        description="The author names exactly as they appear in the reference, preserving order.",
    )

    author_normalized: list[str] | None = Field(
        default=None,
        description="Normalized author names (surname only!)",
    )

    additional_creators: list[str] | None = Field(
        default=None,
        description="Additional creators such as editors, translators, illustrators, or compilers, without roles.",
    )

    publication_place_raw: str | None = Field(
        default=None,
        description="The publication place exactly as it appears in the reference.",
    )

    publication_place_normalized: str | None = Field(
        default=None,
        description="The normalized publication place.",
    )

    publisher: str | None = Field(
        default=None,
        description="The publisher or printer, if stated.",
    )

    edition: str | None = Field(
        default=None,
        description="The edition statement, if present.",
    )

    language: str | None = Field(
        default=None,
        description="The language of the work, if it can be determined from the reference.",
    )

    volume: str | None = Field(
        default=None,
        description="The volume or part designation, if present.",
    )

    physical_format: str | None = Field(
        default=None,
        description="The bibliographic format as stated, such as '8o', '4to', or 'fol.'.",
    )

    publication_year: str | None = Field(
        default=None,
        description="The publication year or date exactly as stated.",
    )

    notes: str | None = Field(
        default=None,
        description="Additional bibliographic information that cannot be assigned to another field.",
    )

    confidence: str  = Field(
        default="unknown",
        description="Overall confidence in the extraction, such as high, medium, or low.",
    )
