from siasa.runs.run_state import RunState, SourceExecutionResult


def test_run_state_stays_success_when_all_sources_succeed() -> None:
    state = RunState.start(run_id="RUN-001")
    state.record_source_result(SourceExecutionResult(source_id="SRC-A", status="success"))
    state.record_source_result(SourceExecutionResult(source_id="SRC-B", status="success"))

    assert state.status == "success"
    assert state.failed_sources == []


def test_run_state_becomes_partial_success_when_one_source_fails() -> None:
    state = RunState.start(run_id="RUN-002")
    state.record_source_result(SourceExecutionResult(source_id="SRC-A", status="success"))
    state.record_source_result(SourceExecutionResult(source_id="SRC-B", status="failed", diagnostics="timeout"))

    assert state.status == "partial_success"
    assert state.failed_sources == ["SRC-B"]


def test_run_state_becomes_failed_when_all_sources_fail() -> None:
    state = RunState.start(run_id="RUN-003")
    state.record_source_result(SourceExecutionResult(source_id="SRC-A", status="failed"))
    state.record_source_result(SourceExecutionResult(source_id="SRC-B", status="failed"))

    assert state.status == "failed"
    assert state.failed_sources == ["SRC-A", "SRC-B"]


def test_source_execution_result_rejects_invalid_status() -> None:
    try:
        SourceExecutionResult(source_id="SRC-A", status="other")
    except ValueError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid source execution status")
