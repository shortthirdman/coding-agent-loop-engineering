from dataclasses import dataclass

import json
from pathlib import Path
from typing import Literal


Provider = Literal["claude", "codex"]

HANDOFF_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["act", "blocked", "ask_human"],
        },
        "step_id": {"type": "string"},
        "action": {"type": "string"},
        "target_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "success_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "decision",
        "step_id",
        "action",
        "target_files",
        "success_evidence",
    ],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class PlanningRequest:
    provider: Provider
    command: tuple[str, ...]
    schema_mode: str
    prompt: str


@dataclass(frozen=True, slots=True)
class InvocationPolicy:
    max_turns: int = 6
    max_budget_usd: float = 3.00
    sandbox: str = "workspace-write"


def build_planning_prompt(
    checkpoint: dict[str, object],
) -> str:
    return (
        "Plan exactly one next action for the active task step.\n"
        "Do not edit files or run mutating commands.\n"
        "Preserve completed steps and revise only invalidated work.\n"
        "Return the requested handoff fields.\n\n"
        "<checkpoint>\n"
        f"{json.dumps(checkpoint, indent=2, sort_keys=True)}"
        "\n</checkpoint>"
    )

def build_planning_request(
    provider: Provider,
    checkpoint: dict[str, object],
    schema_path: str,
) -> PlanningRequest:
    prompt = build_planning_prompt(checkpoint)

    if provider == "claude":
        return PlanningRequest(
            provider=provider,
            command=(
                "claude",
                "--permission-mode",
                "plan",
                "-p",
                prompt,
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(
                    HANDOFF_SCHEMA,
                    separators=(",", ":"),
                ),
            ),
            schema_mode="inline_json_schema",
            prompt=prompt,
        )

    return PlanningRequest(
        provider=provider,
        command=(
            "codex",
            "--ask-for-approval",
            "never",
            "exec",
            "--sandbox",
            "read-only",
            "--json",
            "--output-schema",
            schema_path,
            prompt,
        ),
        schema_mode="schema_file",
        prompt=prompt,
    )


def build_agent_command(
    provider: Provider,
    prompt: str,
    policy: InvocationPolicy,
) -> list[str]:
    if provider == "claude":
        return [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--max-turns",
            str(policy.max_turns),
            "--max-budget-usd",
            f"{policy.max_budget_usd:.2f}",
            "--allowedTools",
            "Read",
            "Edit",
            "Bash",
            prompt,
        ]

    if provider == "codex":
        return [
            "codex",
            "exec",
            "--json",
            "--sandbox",
            policy.sandbox,
            prompt,
        ]

    raise ValueError(f"Unsupported provider: {provider}")


schema_path = "planning_handoff.schema.json"
Path(schema_path).write_text(
    json.dumps(HANDOFF_SCHEMA, indent=2) + "\n",
    encoding="utf-8",
)

checkpoint = {
    "phase": "replanning",
    "plan_revision": 3,
    "active_step": "patch_parser",
    "completed_steps": [
        "reproduce_failure",
        "inspect_parser",
        "add_regression_test",
    ],
    "invalidated_steps": ["patch_parser"],
    "hypothesis": (
        "Blank lines must be skipped before split(':', 1)."
    ),
}

for provider in ("claude", "codex"):
    request = build_planning_request(
        provider,
        checkpoint,
        schema_path,
    )
    print(f"provider={request.provider}")
    print("command_prefix=" + " ".join(request.command[:4]))
    print(f"schema_mode={request.schema_mode}")
    print(
        "checkpoint_in_prompt="
        f"{'<checkpoint>' in request.prompt}"
    )
    print(
        "handoff_fields="
        + ",".join(HANDOFF_SCHEMA["required"])
    )

print(f"schema_file_written={Path(schema_path).exists()}")