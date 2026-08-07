import hashlib
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Literal


Provider = Literal["claude_fixture", "codex_fixture"]


class Phase(str, Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class Contract:
    objective: str
    approved_files: tuple[str, ...]
    max_iterations: int
    human_approval_required: bool = False


@dataclass(frozen=True)
class RunState:
    phase: Phase
    plan_revision: int
    iterations_used: int
    hypothesis: str
    unresolved_steps: int
    last_failure: str | None = None


@dataclass(frozen=True)
class Action:
    strategy: Literal["strip_only", "skip_blank"]
    target_file: str


@dataclass(frozen=True)
class AgentRunResult:
    provider: Provider
    session_handle: str
    event_types: tuple[str, ...]
    changed_files: tuple[str, ...]
    native_stop_reason: str


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    exit_code: int
    fingerprint: str | None
    output: str


@dataclass(frozen=True)
class CompletionDecision:
    transition: Literal[
        "succeed",
        "replan",
        "escalate",
        "fail",
    ]
    reason: str


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def initialize_repository(repo: Path) -> None:
    parser = repo / "src/parser/headers.py"
    test_file = repo / "tests/test_parser.py"

    parser.parent.mkdir(parents=True)
    test_file.parent.mkdir(parents=True)

    (repo / "src/__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (repo / "src/parser/__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    parser.write_text(
        """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers
""",
        encoding="utf-8",
    )

    test_file.write_text(
        """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.parser.headers import parse_headers

block = "Host: example.com\\n\\nAccept: application/json"
expected = {
    "host": "example.com",
    "accept": "application/json",
}
assert parse_headers(block) == expected
print("parser_acceptance=passed")
""",
        encoding="utf-8",
    )

    run_git(repo, "init", "-q")
    run_git(
        repo,
        "config",
        "user.email",
        "agent@example.com",
    )
    run_git(
        repo,
        "config",
        "user.name",
        "Agent Test",
    )
    run_git(repo, "add", ".")
    run_git(
        repo,
        "commit",
        "-qm",
        "baseline",
    )


def allocate_worktree(
    repo: Path,
    worktree: Path,
) -> None:
    run_git(
        repo,
        "worktree",
        "add",
        "-q",
        "-b",
        "agent/parser-fix",
        str(worktree),
        "HEAD",
    )


def verify(repo: Path) -> VerificationResult:
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "tests/test_parser.py",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.strip()

    fingerprint = None

    if "not enough values to unpack" in output:
        fingerprint = (
            "ValueError:"
            "not_enough_values_to_unpack"
        )
    elif completed.returncode != 0:
        fingerprint = (
            "verification:other_failure"
        )

    return VerificationResult(
        passed=completed.returncode == 0,
        exit_code=completed.returncode,
        fingerprint=fingerprint,
        output=output,
    )


def apply_action(
    repo: Path,
    provider: Provider,
    action: Action,
    attempt: int,
) -> AgentRunResult:
    parser = repo / action.target_file

    if action.strategy == "strip_only":
        source = """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers
"""
    else:
        source = """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers
"""

    parser.write_text(
        source,
        encoding="utf-8",
    )

    changed_files = tuple(
        line
        for line in run_git(
            repo,
            "diff",
            "--name-only",
        ).splitlines()
        if line
    )

    if provider == "claude_fixture":
        events = (
            "system",
            "assistant",
            "result",
        )
        session = (
            f"claude-fixture-session-{attempt}"
        )
        stop_reason = "success"
    else:
        events = (
            "thread.started",
            "turn.started",
            "item.completed",
            "turn.completed",
        )
        session = (
            f"codex-fixture-thread-{attempt}"
        )
        stop_reason = "turn.completed"

    return AgentRunResult(
        provider=provider,
        session_handle=session,
        event_types=events,
        changed_files=changed_files,
        native_stop_reason=stop_reason,
    )


def patch_hash(repo: Path) -> str:
    patch = run_git(
        repo,
        "diff",
        "--binary",
    )

    return hashlib.sha256(
        patch.encode("utf-8")
    ).hexdigest()[:16]


def can_start(
    contract: Contract,
    state: RunState,
) -> bool:
    return (
        state.phase
        in {
            Phase.PLANNING,
            Phase.REPLANNING,
        }
        and state.iterations_used
        < contract.max_iterations
    )


def choose_action(
    state: RunState,
) -> Action:
    if state.plan_revision == 1:
        return Action(
            strategy="strip_only",
            target_file=(
                "src/parser/headers.py"
            ),
        )

    return Action(
        strategy="skip_blank",
        target_file=(
            "src/parser/headers.py"
        ),
    )


def classify(
    previous: VerificationResult,
    current: VerificationResult,
) -> str:
    if (
        not current.passed
        and current.fingerprint
        == previous.fingerprint
    ):
        return "failed_hypothesis"

    if not current.passed:
        return "verification_failure"

    return "none"


def decide_completion(
    *,
    verification_passed: bool,
    unresolved_steps: int,
    budget_remaining: bool,
    human_approval_required: bool,
) -> CompletionDecision:
    if human_approval_required:
        return CompletionDecision(
            "escalate",
            "human_approval_required",
        )

    if not budget_remaining:
        return CompletionDecision(
            "fail",
            "outer_budget_exhausted",
        )

    if not verification_passed:
        return CompletionDecision(
            "replan",
            "verification_failed",
        )

    if unresolved_steps != 0:
        return CompletionDecision(
            "replan",
            f"unresolved_steps:{unresolved_steps}",
        )

    return CompletionDecision(
        "succeed",
        "verified_completion",
    )


contract = Contract(
    objective=(
        "Fix blank-line handling in "
        "parse_headers and preserve "
        "standard header parsing."
    ),
    approved_files=(
        "src/parser/headers.py",
    ),
    max_iterations=3,
)

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    repository = root / "repository"
    worktree = root / "parser-fix"

    repository.mkdir()

    initialize_repository(repository)
    allocate_worktree(
        repository,
        worktree,
    )

    state = RunState(
        phase=Phase.INITIALIZING,
        plan_revision=1,
        iterations_used=0,
        hypothesis=(
            "Strip each line before splitting."
        ),
        unresolved_steps=1,
    )

    print(
        f"objective={contract.objective}"
    )

    state = replace(
        state,
        phase=Phase.PLANNING,
    )
    print(f"phase={state.phase.value}")

    baseline = verify(worktree)

    print(
        "reproduction="
        f"passed:{baseline.passed},"
        f"fingerprint:{baseline.fingerprint}"
    )

    providers: tuple[
        Provider,
        ...,
    ] = (
        "claude_fixture",
        "codex_fixture",
    )

    for provider in providers:
        if not can_start(
            contract,
            state,
        ):
            state = replace(
                state,
                phase=Phase.FAILED,
            )
            print(
                "terminal=failed "
                "reason=budget_or_state_block"
            )
            break

        action = choose_action(state)

        state = replace(
            state,
            phase=Phase.EXECUTING,
            iterations_used=(
                state.iterations_used + 1
            ),
        )

        print(
            f"iteration="
            f"{state.iterations_used} "
            f"provider={provider} "
            f"plan_revision="
            f"{state.plan_revision} "
            f"strategy={action.strategy}"
        )

        run_result = apply_action(
            worktree,
            provider,
            action,
            state.iterations_used,
        )

        diff_allowed = (
            set(run_result.changed_files)
            <= set(contract.approved_files)
        )

        print(
            f"worker_stop="
            f"{run_result.native_stop_reason} "
            f"session="
            f"{run_result.session_handle} "
            f"events="
            f"{len(run_result.event_types)} "
            f"diff_allowed={diff_allowed}"
        )

        if not diff_allowed:
            state = replace(
                state,
                phase=Phase.FAILED,
            )
            print(
                "terminal=failed "
                "reason=scope_violation"
            )
            break

        state = replace(
            state,
            phase=Phase.VERIFYING,
        )
        result = verify(worktree)

        print(
            "verification="
            f"passed:{result.passed},"
            f"exit_code:{result.exit_code},"
            f"fingerprint:"
            f"{result.fingerprint}"
        )

        if result.passed:
            state = replace(
                state,
                unresolved_steps=0,
            )

            completion = decide_completion(
                verification_passed=True,
                unresolved_steps=(
                    state.unresolved_steps
                ),
                budget_remaining=(
                    state.iterations_used
                    <= contract.max_iterations
                ),
                human_approval_required=(
                    contract
                    .human_approval_required
                ),
            )

            print(
                "completion_gate="
                f"{completion.transition} "
                f"reason={completion.reason}"
            )

            if (
                completion.transition
                == "succeed"
            ):
                state = replace(
                    state,
                    phase=Phase.SUCCEEDED,
                )

                print(
                    "terminal=succeeded "
                    "reason=verified_completion "
                    f"patch_sha256="
                    f"{patch_hash(worktree)}"
                )
                print(
                    "retention="
                    "retain_branch,"
                    "retain_evidence,"
                    "open_pr"
                )

            elif (
                completion.transition
                == "escalate"
            ):
                print(
                    "terminal=escalated "
                    f"reason={completion.reason}"
                )

            else:
                state = replace(
                    state,
                    phase=Phase.FAILED,
                )
                print(
                    "terminal=failed "
                    f"reason={completion.reason}"
                )

            break

        failure_class = classify(
            baseline,
            result,
        )

        print(
            f"failure_class={failure_class} "
            "next_transition=replan"
        )

        state = replace(
            state,
            phase=Phase.REPLANNING,
            plan_revision=(
                state.plan_revision + 1
            ),
            hypothesis=(
                "Skip blank lines before "
                "split(':', 1)."
            ),
            last_failure=(
                result.fingerprint
            ),
        )
        baseline = result

        print(
            f"replanned_revision="
            f"{state.plan_revision} "
            f"hypothesis={state.hypothesis}"
        )