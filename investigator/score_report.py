from dataclasses import dataclass
import json
from pathlib import Path

from investigator.report import InvestigationReport


@dataclass(frozen=True)
class CiteCheck:
    path: str
    line: int | None = None


@dataclass(frozen=True)
class AnswerKey:
    question: str
    must_cite: list[CiteCheck]


@dataclass(frozen=True)
class ScoreResult:
    passed: bool
    failed: list[str]


def load_answer_key(path: Path) -> AnswerKey:
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = [
        CiteCheck(path=item["path"], line=item.get("line"))
        for item in data["must_cite"]
    ]
    return AnswerKey(question=data["question"], must_cite=checks)


def score_report(report: InvestigationReport, key: AnswerKey) -> ScoreResult:
    failed: list[str] = []
    for check in key.must_cite:
        if _citation_matches(report, check):
            continue
        if check.line is None:
            failed.append(f"missing citation for {check.path}")
        else:
            failed.append(f"missing citation for {check.path} line {check.line}")
    return ScoreResult(passed=not failed, failed=failed)


def _citation_matches(report: InvestigationReport, check: CiteCheck) -> bool:
    for citation in report.citations:
        if citation.path != check.path:
            continue
        if check.line is None:
            return True
        if citation.start_line <= check.line <= citation.end_line:
            return True
    return False
