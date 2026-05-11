from __future__ import annotations

from dataclasses import dataclass, field

_ALLOWED_SOURCE_STATUSES = {"success", "failed"}


@dataclass(frozen=True)
class SourceExecutionResult:
    source_id: str
    status: str
    diagnostics: str = ""

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_SOURCE_STATUSES:
            raise ValueError("status must be one of success, failed")
        if not self.source_id:
            raise ValueError("source_id is required")


@dataclass
class RunState:
    run_id: str
    status: str = "success"
    source_results: list[SourceExecutionResult] = field(default_factory=list)

    @classmethod
    def start(cls, run_id: str) -> "RunState":
        return cls(run_id=run_id)

    @property
    def failed_sources(self) -> list[str]:
        return [result.source_id for result in self.source_results if result.status == "failed"]

    def record_source_result(self, result: SourceExecutionResult) -> None:
        self.source_results.append(result)
        statuses = [entry.status for entry in self.source_results]
        if statuses and all(status == "failed" for status in statuses):
            self.status = "failed"
        elif "failed" in statuses and "success" in statuses:
            self.status = "partial_success"
        else:
            self.status = "success"
