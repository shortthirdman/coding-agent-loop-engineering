from dataclasses import dataclass
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PlanStep:
    id: str
    goal: str
    status: StepStatus
    depends_on: tuple[str, ...] = ()
    mutation_scope: tuple[str, ...] = ()
    success_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionProposal:
    step_id: str
    action: str
    mutating: bool
    target_files: tuple[str, ...]
    success_evidence: tuple[str, ...]


def ready_steps(steps: tuple[PlanStep, ...]) -> list[PlanStep]:
    status_by_id = {step.id: step.status for step in steps}

    return [
        step
        for step in steps
        if step.status == StepStatus.PENDING
        and all(
            status_by_id[dependency] == StepStatus.COMPLETED
            for dependency in step.depends_on
        )
    ]


def select_next_action(
    steps: tuple[PlanStep, ...],
) -> ActionProposal:
    candidates = ready_steps(steps)
    if not candidates:
        raise RuntimeError("no_ready_step")

    step = candidates[0]
    return ActionProposal(
        step_id=step.id,
        action=step.goal,
        mutating=bool(step.mutation_scope),
        target_files=step.mutation_scope,
        success_evidence=step.success_evidence,
    )


steps = (
    PlanStep(
        id="reproduce_failure",
        goal="Reproduce the failure.",
        status=StepStatus.COMPLETED,
    ),
    PlanStep(
        id="inspect_parser",
        goal="Inspect the parser.",
        status=StepStatus.COMPLETED,
        depends_on=("reproduce_failure",),
    ),
    PlanStep(
        id="add_regression_test",
        goal="Add the blank-line regression test.",
        status=StepStatus.PENDING,
        depends_on=("inspect_parser",),
        mutation_scope=("tests/parser/test_headers.py",),
        success_evidence=("new test fails before the patch",),
    ),
    PlanStep(
        id="patch_parser",
        goal="Skip blank lines before splitting.",
        status=StepStatus.PENDING,
        depends_on=("inspect_parser",),
        mutation_scope=("src/parser/headers.py",),
        success_evidence=("targeted test passes",),
    ),
)

candidates = ready_steps(steps)
selected = select_next_action(steps)

print("ready_steps=" + ",".join(step.id for step in candidates))
print(f"selected_step={selected.step_id}")
print(f"mutating={selected.mutating}")
print("target_files=" + ",".join(selected.target_files))
print("success_evidence=" + ";".join(selected.success_evidence))