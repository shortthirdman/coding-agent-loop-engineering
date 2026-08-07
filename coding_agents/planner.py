from dataclasses import dataclass, field, replace
from enum import Enum

class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PlanStep:
    id: str
    goal: str
    status: StepStatus
    depends_on: tuple[str, ...] = ()
    mutation_scope: tuple[str, ...] = ()
    success_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskPlan:
    revision: int
    hypothesis: str
    steps: tuple[PlanStep, ...] = field(default_factory=tuple)


def validate_plan(plan: TaskPlan) -> list[str]:
    _errors: list[str] = []
    step_ids = [_step.id for _step in plan.steps]
    known_ids = set(step_ids)

    if len(step_ids) != len(known_ids):
        _errors.append("duplicate_step_id")

    for step in plan.steps:
        unknown = set(step.depends_on) - known_ids
        if unknown:
            _errors.append(
                f"unknown_dependency:{step.id}:"
                f"{','.join(sorted(unknown))}"
            )

        if step.id in step.depends_on:
            _errors.append(f"self_dependency:{step.id}")

    return _errors


def revise_after_failed_verification(
    plan: TaskPlan,
    failed_step_id: str,
    new_hypothesis: str,
) -> TaskPlan:
    invalidated = {failed_step_id}
    changed = True

    while changed:
        changed = False
        for step in plan.steps:
            if (
                step.id not in invalidated
                and any(
                    dependency in invalidated
                    for dependency in step.depends_on
                )
            ):
                invalidated.add(step.id)
                changed = True

    revised_steps: list[PlanStep] = []

    for step in plan.steps:
        if step.id == failed_step_id:
            revised_steps.append(
                replace(step, status=StepStatus.INVALIDATED)
            )
        elif step.id in invalidated:
            revised_steps.append(
                replace(step, status=StepStatus.PENDING)
            )
        else:
            revised_steps.append(step)

    return replace(
        plan,
        revision=plan.revision + 1,
        hypothesis=new_hypothesis,
        steps=tuple(revised_steps),
    )


plan = TaskPlan(
    revision=1,
    hypothesis="The parser sends blank lines into split(':', 1).",
    steps=(
        PlanStep(
            id="reproduce_failure",
            goal="Reproduce the blank-line ValueError.",
            status=StepStatus.COMPLETED,
            success_evidence=("ValueError fingerprint recorded",),
        ),
        PlanStep(
            id="inspect_parser",
            goal="Inspect the parser path that handles each line.",
            status=StepStatus.ACTIVE,
            depends_on=("reproduce_failure",),
            success_evidence=("failing line identified",),
        ),
        PlanStep(
            id="add_regression_test",
            goal="Add a test for the blank separator line.",
            status=StepStatus.PENDING,
            depends_on=("inspect_parser",),
            mutation_scope=("tests/parser/test_headers.py",),
            success_evidence=("new test fails before the patch",),
        ),
        PlanStep(
            id="patch_parser",
            goal="Apply the smallest parser fix.",
            status=StepStatus.PENDING,
            depends_on=("inspect_parser",),
            mutation_scope=("src/parser/headers.py",),
            success_evidence=("targeted test passes",),
        ),
        PlanStep(
            id="verify_parser",
            goal="Run targeted and regression checks.",
            status=StepStatus.PENDING,
            depends_on=("add_regression_test", "patch_parser"),
            success_evidence=(
                "targeted test passes",
                "compileall passes",
            ),
        ),
    ),
)

errors = validate_plan(plan)

print(f"plan_valid={not errors}")
print(f"revision={plan.revision}")
print(f"hypothesis={plan.hypothesis}")

for step in plan.steps:
    print(
        f"step={step.id} "
        f"status={step.status.value} "
        f"depends_on={','.join(step.depends_on) or 'none'}"
    )


attempted_plan = TaskPlan(
    revision=2,
    hypothesis=(
        "Stripping each line before splitting will fix the parser."
    ),
    steps=(
        PlanStep(
            id="reproduce_failure",
            status=StepStatus.COMPLETED,
        ),
        PlanStep(
            id="inspect_parser",
            status=StepStatus.COMPLETED,
            depends_on=("reproduce_failure",),
        ),
        PlanStep(
            id="add_regression_test",
            status=StepStatus.COMPLETED,
            depends_on=("inspect_parser",),
        ),
        PlanStep(
            id="patch_parser",
            status=StepStatus.COMPLETED,
            depends_on=("inspect_parser",),
        ),
        PlanStep(
            id="verify_parser",
            status=StepStatus.ACTIVE,
            depends_on=("add_regression_test", "patch_parser"),
        ),
    ),
)

revised = revise_after_failed_verification(
    attempted_plan,
    failed_step_id="patch_parser",
    new_hypothesis=(
        "Blank lines must be skipped before split(':', 1)."
    ),
)

print(f"plan_revision={revised.revision}")
print(f"new_hypothesis={revised.hypothesis}")
for step in revised.steps:
    print(f"{step.id}={step.status.value}")