from dataclasses import dataclass
from enum import Enum


class SupervisorDecision(str, Enum):
    VERIFY = "verify"
    REPLAN = "replan"
    SUCCEED = "succeed"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class ActionProposal:
    step_id: str
    target_files: tuple[str, ...]
    success_evidence: tuple[str, ...]


@dataclass(frozen=True)
class WorkerHandoff:
    step_id: str
    tool_calls: tuple[str, ...]
    target_files: tuple[str, ...]
    expected_evidence: tuple[str, ...]


@dataclass(frozen=True)
class AgentRunResult:
    provider: str
    claimed_complete: bool
    changed_files: tuple[str, ...]
    summary: str


def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers


def verify_parser_behavior() -> tuple[bool, str]:
    sample = "Host: example.com\n\nAccept: application/json"
    try:
        parsed = parse_headers(sample)
    except ValueError as exc:
        return False, f"ValueError:{exc}"
    expected = {
        "host": "example.com",
        "accept": "application/json",
    }
    return parsed == expected, f"parsed={parsed}"


def supervise(
        result: AgentRunResult,
) -> tuple[SupervisorDecision, str]:
    if result.changed_files:
        return (
            SupervisorDecision.VERIFY,
            "repository changed; verification is required",
        )
    passed, evidence = verify_parser_behavior()
    if result.claimed_complete and not passed:
        return (
            SupervisorDecision.REPLAN,
            f"completion claim rejected; {evidence}",
        )
    if passed:
        return SupervisorDecision.SUCCEED, evidence
    return SupervisorDecision.REPLAN, evidence


MUTATING_TOOLS = {
    "edit_file",
    "apply_patch",
    "write_file",
}


def validate_handoff(
    selected: ActionProposal,
    handoff: WorkerHandoff,
) -> list[str]:
    errors: list[str] = []

    if handoff.step_id != selected.step_id:
        errors.append("step_mismatch")

    mutating_calls = [
        name
        for name in handoff.tool_calls
        if name in MUTATING_TOOLS
    ]
    if len(mutating_calls) > 1:
        errors.append("multiple_mutating_tools")

    unauthorized_files = (
        set(handoff.target_files)
        - set(selected.target_files)
    )
    if unauthorized_files:
        errors.append(
            "unauthorized_files:"
            + ",".join(sorted(unauthorized_files))
        )

    if not handoff.expected_evidence:
        errors.append("missing_success_evidence")

    return errors

result = AgentRunResult(
    provider="codex",
    claimed_complete=True,
    changed_files=(),
    summary="The parser task appears complete.",
)
decision, reason = supervise(result)
print(f"provider={result.provider}")
print(f"agent_claimed_complete={result.claimed_complete}")
print(f"supervisor_decision={decision.value}")
print(f"reason={reason}")

selected = ActionProposal(
    step_id="add_regression_test",
    target_files=("tests/parser/test_headers.py",),
    success_evidence=("new test fails before the patch",),
)

handoffs = {
    "bounded": WorkerHandoff(
        step_id="add_regression_test",
        tool_calls=("read_file", "edit_file"),
        target_files=("tests/parser/test_headers.py",),
        expected_evidence=("new test fails before the patch",),
    ),
    "overbroad": WorkerHandoff(
        step_id="add_regression_test",
        tool_calls=("edit_file", "apply_patch"),
        target_files=(
            "tests/parser/test_headers.py",
            "src/parser/headers.py",
        ),
        expected_evidence=(),
    ),
}

for name, handoff in handoffs.items():
    errors = validate_handoff(selected, handoff)
    print(
        f"handoff={name} "
        f"accepted={not errors} "
        f"errors={','.join(errors) or 'none'}"
    )