from dataclasses import dataclass
from enum import Enum


class TriggerKind(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"


@dataclass(frozen=True)
class Trigger:
    kind: TriggerKind
    source: str
    dedupe_key: str
    received_at: str


@dataclass(frozen=True)
class StartDecision:
    start: bool
    reason: str


def evaluate_trigger(
    trigger: Trigger,
    seen: set[str],
    *,
    terminal: bool,
    budget_available: bool,
    run_active: bool = False,
) -> StartDecision:
    if terminal:
        return StartDecision(
            False,
            "task_already_terminal",
        )

    if run_active:
        return StartDecision(
            False,
            "run_already_active",
        )

    if trigger.dedupe_key in seen:
        return StartDecision(
            False,
            "duplicate_trigger",
        )

    if not budget_available:
        return StartDecision(
            False,
            "budget_unavailable",
        )

    return StartDecision(
        True,
        "start_iteration",
    )


seen = {
    "schedule:2026-07-29T09:00Z"
}

triggers = (
    Trigger(
        kind=TriggerKind.MANUAL,
        source="operator",
        dedupe_key="manual:42",
        received_at=(
            "2026-07-29T09:05:00Z"
        ),
    ),
    Trigger(
        kind=TriggerKind.SCHEDULED,
        source="hourly",
        dedupe_key=(
            "schedule:2026-07-29T09:00Z"
        ),
        received_at=(
            "2026-07-29T09:05:10Z"
        ),
    ),
    Trigger(
        kind=TriggerKind.EVENT,
        source="git-push",
        dedupe_key="push:abc123",
        received_at=(
            "2026-07-29T09:05:20Z"
        ),
    ),
)

for trigger in triggers:
    decision = evaluate_trigger(
        trigger,
        seen,
        terminal=False,
        budget_available=True,
    )

    print(
        f"kind={trigger.kind.value} "
        f"key={trigger.dedupe_key} "
        f"start={decision.start} "
        f"reason={decision.reason}"
    )

    if decision.start:
        seen.add(trigger.dedupe_key)

new_event = Trigger(
    kind=TriggerKind.EVENT,
    source="git-push",
    dedupe_key="push:def456",
    received_at="2026-07-29T09:06:00Z",
)

terminal_decision = evaluate_trigger(
    new_event,
    seen,
    terminal=True,
    budget_available=True,
)

active_decision = evaluate_trigger(
    new_event,
    seen,
    terminal=False,
    budget_available=True,
    run_active=True,
)

print(f"terminal_event={terminal_decision}")
print(f"active_run_event={active_decision}")