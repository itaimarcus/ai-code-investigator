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


class RunCounts(BaseModel):
    passed: int = Field(
        ge=0,
        description="How many tests passed.",
    )
    total: int = Field(
        ge=0,
        description="How many tests ran.",
    )

    @model_validator(mode="after")
    def passed_not_above_total(self) -> "RunCounts":
        if self.passed > self.total:
            raise ValueError("passed must be less than or equal to total")
        return self


class RepairReport(BaseModel):
    summary: str = Field(
        description="What was wrong and what changed, based only on what the tools showed.",
    )
    files_changed: list[str] = Field(
        description="Paths relative to the repository root that were edited. Empty if nothing was written.",
    )
    tests_before: RunCounts = Field(
        description="Passed and total from the first run_tests call.",
    )
    tests_after: RunCounts = Field(
        description="Passed and total from the last run_tests call.",
    )
    tests_failed_names: list[str] = Field(
        description="Exact pytest names that failed. Empty if none failed.",
    )
    success: bool = Field(
        description="True only when every test passed after the repair.",
    )

    @model_validator(mode="after")
    def success_from_counts(self) -> "RepairReport":
        self.success = (
            self.tests_after.total > 0
            and self.tests_after.passed == self.tests_after.total
        )
        return self
