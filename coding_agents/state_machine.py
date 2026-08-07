from dataclasses import dataclass, replace
from enum import Enum

class Phase(str, Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ESCALATED = "escalated"

class Event(str, Enum):
    TASK_INITIALIZED = "task_initialized"
    PLAN_CREATED = "plan_created"
    TOOL_COMPLETED = "tool_completed"
    VERIFICATION_REQUESTED = "verification_requested"
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_PASSED = "verification_passed"
    POLICY_BLOCKED = "policy_blocked"

TRANSITIONS = {
    (
        Phase.INITIALIZING,
        Event.TASK_INITIALIZED,
    ): Phase.PLANNING,
    (
        Phase.PLANNING,
        Event.PLAN_CREATED,
    ): Phase.EXECUTING,
    (
        Phase.EXECUTING,
        Event.TOOL_COMPLETED,
    ): Phase.OBSERVING,
    (
        Phase.OBSERVING,
        Event.VERIFICATION_REQUESTED,
    ): Phase.VERIFYING,
    (
        Phase.VERIFYING,
        Event.VERIFICATION_FAILED,
    ): Phase.REPLANNING,
    (
        Phase.VERIFYING,
        Event.VERIFICATION_PASSED,
    ): Phase.SUCCEEDED,
}

@dataclass(frozen=True)
class MachineState:
    phase: Phase = Phase.INITIALIZING
    last_event: Event | None = None

def transition(
    _state: MachineState,
    _event: Event,
) -> MachineState:
    if _event == Event.POLICY_BLOCKED:
        return replace(
            _state,
            phase=Phase.ESCALATED,
            last_event=_event,
        )
    target = TRANSITIONS.get((_state.phase, _event))
    if target is None:
        raise ValueError(
            f"illegal_transition:"
            f"{_state.phase.value}+{_event.value}"
        )
    return replace(
        _state,
        phase=target,
        last_event=_event,
    )

state = MachineState()
events = (
    Event.TASK_INITIALIZED,
    Event.PLAN_CREATED,
    Event.TOOL_COMPLETED,
    Event.VERIFICATION_REQUESTED,
    Event.VERIFICATION_FAILED,
)

for event in events:
    previous = state.phase
    state = transition(state, event)
    print(
        f"{previous.value:12} "
        f"--{event.value:23}--> "
        f"{state.phase.value}"
    )
try:
    transition(
        MachineState(phase=Phase.EXECUTING),
        Event.VERIFICATION_PASSED,
    )
except ValueError as exc:
    print(f"rejected={exc}")