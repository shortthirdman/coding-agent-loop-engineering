import json
from dataclasses import dataclass
from typing import Literal


Provider = Literal["claude", "codex"]


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: float | None = None
    turns: int | None = None


@dataclass(frozen=True)
class AgentRunResult:
    provider: Provider
    session_handle: str | None
    final_message: str
    native_stop_reason: str
    usage: Usage
    event_types: tuple[str, ...]


def parse_json_lines(
    text: str,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid_json_line:{line_number}"
            ) from exc

    return events


def normalize_claude(
    text: str,
) -> AgentRunResult:
    events = parse_json_lines(text)
    session_handle: str | None = None
    final_message = ""
    stop_reason = "missing_result"
    usage = Usage()

    for event in events:
        if isinstance(event.get("session_id"), str):
            session_handle = str(
                event["session_id"]
            )

        if event.get("type") == "result":
            final_message = str(
                event.get("result", "")
            )
            stop_reason = str(
                event.get("subtype", "result")
            )

            native_usage = event.get("usage", {})
            if not isinstance(native_usage, dict):
                native_usage = {}

            usage = Usage(
                input_tokens=int(
                    native_usage.get(
                        "input_tokens",
                        0,
                    )
                ),
                output_tokens=int(
                    native_usage.get(
                        "output_tokens",
                        0,
                    )
                ),
                cost_usd=float(
                    event.get(
                        "total_cost_usd",
                        0.0,
                    )
                ),
                turns=int(
                    event.get("num_turns", 0)
                ),
            )

    return AgentRunResult(
        provider="claude",
        session_handle=session_handle,
        final_message=final_message,
        native_stop_reason=stop_reason,
        usage=usage,
        event_types=tuple(
            str(event.get("type"))
            for event in events
        ),
    )


def normalize_codex(
    text: str,
) -> AgentRunResult:
    events = parse_json_lines(text)
    session_handle: str | None = None
    final_message = ""
    stop_reason = "missing_turn_result"
    usage = Usage()

    for event in events:
        event_type = event.get("type")

        if event_type == "thread.started":
            session_handle = str(
                event.get("thread_id")
            )

        elif event_type == "item.completed":
            item = event.get("item", {})

            if (
                isinstance(item, dict)
                and item.get("type")
                == "agent_message"
            ):
                final_message = str(
                    item.get("text", "")
                )

        elif event_type == "turn.completed":
            native_usage = event.get("usage", {})
            if not isinstance(native_usage, dict):
                native_usage = {}

            usage = Usage(
                input_tokens=int(
                    native_usage.get(
                        "input_tokens",
                        0,
                    )
                ),
                output_tokens=int(
                    native_usage.get(
                        "output_tokens",
                        0,
                    )
                ),
                cached_input_tokens=int(
                    native_usage.get(
                        "cached_input_tokens",
                        0,
                    )
                ),
            )
            stop_reason = "turn.completed"

        elif event_type in {
            "turn.failed",
            "error",
        }:
            stop_reason = str(event_type)

    return AgentRunResult(
        provider="codex",
        session_handle=session_handle,
        final_message=final_message,
        native_stop_reason=stop_reason,
        usage=usage,
        event_types=tuple(
            str(event.get("type"))
            for event in events
        ),
    )


claude_stream = "\n".join(
    (
        json.dumps(
            {
                "type": "system",
                "subtype": "init",
                "session_id":
                    "claude-session-1842",
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                        }
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "session_id":
                    "claude-session-1842",
                "result": (
                    "Updated the parser to "
                    "skip blank lines."
                ),
                "total_cost_usd": 0.018,
                "num_turns": 2,
                "usage": {
                    "input_tokens": 3421,
                    "output_tokens": 284,
                },
            }
        ),
    )
)

codex_stream = "\n".join(
    (
        json.dumps(
            {
                "type": "thread.started",
                "thread_id":
                    "codex-thread-7331",
            }
        ),
        json.dumps(
            {"type": "turn.started"}
        ),
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_1",
                    "type": "file_change",
                    "path":
                        "src/parser/headers.py",
                },
            }
        ),
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_2",
                    "type": "agent_message",
                    "text": (
                        "Updated the parser to "
                        "skip blank lines."
                    ),
                },
            }
        ),
        json.dumps(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 24763,
                    "cached_input_tokens":
                        24448,
                    "output_tokens": 122,
                    "reasoning_output_tokens":
                        0,
                },
            }
        ),
    )
)

for result in (
    normalize_claude(claude_stream),
    normalize_codex(codex_stream),
):
    print(
        f"provider={result.provider} "
        f"session={result.session_handle} "
        f"events={len(result.event_types)} "
        f"stop={result.native_stop_reason}"
    )
    print(
        f"final_message={result.final_message}"
    )
    print(
        "usage="
        f"input:{result.usage.input_tokens},"
        f"output:{result.usage.output_tokens},"
        f"cached:"
        f"{result.usage.cached_input_tokens},"
        f"cost:{result.usage.cost_usd}"
    )