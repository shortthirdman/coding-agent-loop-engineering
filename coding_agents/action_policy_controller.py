from dataclasses import dataclass, replace
from enum import Enum
from fnmatch import fnmatchcase

class Phase(str, Enum):
    REPLANNING = "replanning"
    EXECUTING = "executing"
    ESCALATED = "escalated"

@dataclass(frozen=True)
class Policy:
    writable_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    max_changed_files: int

@dataclass(frozen=True)
class RunState:
    phase: Phase
    selected_action: str | None = None
    stop_reason: str | None = None

def matches(
    path: str,
    patterns: tuple[str, ...],
) -> bool:
    return any(
        fnmatchcase(path, pattern)
        for pattern in patterns
    )

def validate_change_set(
    files: tuple[str, ...],
    policy: Policy,
) -> list[str]:
    reasons: list[str] = []
    if len(files) > policy.max_changed_files:
        reasons.append("changed_file_limit_exceeded")
    for path in files:
        if matches(path, policy.protected_paths):
            reasons.append(f"protected_path:{path}")
        elif not matches(path, policy.writable_paths):
            reasons.append(
                f"outside_writable_scope:{path}"
            )
    return reasons

def select_action(
    state: RunState,
    action: str,
    files: tuple[str, ...],
    policy: Policy,
) -> RunState:
    reasons = validate_change_set(files, policy)
    if reasons:
        return replace(
            state,
            phase=Phase.ESCALATED,
            stop_reason=";".join(reasons),
        )
    return replace(
        state,
        phase=Phase.EXECUTING,
        selected_action=action,
    )

policy = Policy(
    writable_paths=(
        "src/parser/**",
        "tests/parser/**",
    ),
    protected_paths=(
        "migrations/**",
        "infrastructure/**",
    ),
    max_changed_files=4,
)
checkpoint = RunState(phase=Phase.REPLANNING)
proposals = (
    (
        "inspect parser and add regression test",
        (
            "src/parser/headers.py",
            "tests/parser/test_headers.py",
        ),
    ),
    (
        "change migration helper",
        (
            "src/parser/headers.py",
            "migrations/shared.py",
        ),
    ),
)
for action, files in proposals:
    result = select_action(
        checkpoint,
        action,
        files,
        policy,
    )
    print(f"action={action}")
    print(f"phase={result.phase.value}")
    print(f"stop_reason={result.stop_reason or 'none'}")