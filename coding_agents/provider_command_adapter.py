from dataclasses import dataclass
from shlex import join
from typing import Literal


Provider = Literal["claude", "codex"]


@dataclass(frozen=True)
class WorkerPolicy:
    max_turns: int = 6
    max_budget_usd: float = 3.00
    sandbox: str = "workspace-write"
    approval_policy: str = "never"


@dataclass(frozen=True)
class WorkerInvocation:
    provider: Provider
    command: tuple[str, ...]
    session_handle: str | None
    resumed: bool


def build_worker_invocation(
    provider: Provider,
    prompt: str,
    policy: WorkerPolicy,
    session_handle: str | None = None,
    recorded_sandbox: str | None = None,
) -> WorkerInvocation:
    if provider == "claude":
        command = ["claude", "-p"]

        if session_handle:
            command.extend(["--resume", session_handle])

        command.extend(
            [
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                "acceptEdits",
                "--max-turns",
                str(policy.max_turns),
                "--max-budget-usd",
                f"{policy.max_budget_usd:.2f}",
                "--tools",
                "Bash,Edit,Read",
                "--allowedTools",
                "Read",
                "Edit",
                "Bash(git diff *)",
                "Bash(pytest *)",
                prompt,
            ]
        )

        return WorkerInvocation(
            provider=provider,
            command=tuple(command),
            session_handle=session_handle,
            resumed=session_handle is not None,
        )

    if session_handle:
        if recorded_sandbox != policy.sandbox:
            raise ValueError(
                "codex_resume_policy_mismatch:"
                f"{recorded_sandbox}!={policy.sandbox}"
            )

        command = [
            "codex",
            "exec",
            "resume",
            session_handle,
            "--json",
            prompt,
        ]
    else:
        command = [
            "codex",
            "exec",
            "--json",
            "--sandbox",
            policy.sandbox,
            "--ask-for-approval",
            policy.approval_policy,
            prompt,
        ]

    return WorkerInvocation(
        provider=provider,
        command=tuple(command),
        session_handle=session_handle,
        resumed=session_handle is not None,
    )


policy = WorkerPolicy()
prompt = (
    "Execute step patch_parser. "
    "Modify only src/parser/headers.py. "
    "Skip blank lines before split(':', 1). "
    "Return the resulting diff."
)

cases = (
    ("claude", None, None),
    ("claude", "claude-session-1842", None),
    ("codex", None, None),
    (
        "codex",
        "codex-thread-7331",
        "workspace-write",
    ),
)

for provider, session_handle, recorded_sandbox in cases:
    invocation = build_worker_invocation(
        provider=provider,
        prompt=prompt,
        policy=policy,
        session_handle=session_handle,
        recorded_sandbox=recorded_sandbox,
    )

    print(
        f"provider={provider} "
        f"resumed={invocation.resumed} "
        f"command={join(invocation.command)}"
    )