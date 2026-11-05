from pydantic import BaseModel, Field, model_validator


class FileReference(BaseModel):
    path: str = Field(
        min_length=1,
        description="Path relative to the repository root, for example inventory/products.py.",
    )
    start_line: int = Field(
        ge=1,
        description="First line of the cited range, 1-based and inclusive.",
    )
    end_line: int = Field(
        ge=1,
        description="Last line of the cited range, 1-based and inclusive. Same as start_line for a single line.",
    )

    @model_validator(mode="after")
    def end_at_or_after_start(self) -> "FileReference":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class InvestigationReport(BaseModel):
    summary: str = Field(
        description="Short conclusion in words, based only on what the tools showed.",
    )
    citations: list[FileReference] = Field(
        description="File and line ranges that support the summary. Empty if there is nothing honest to cite.",
    )
