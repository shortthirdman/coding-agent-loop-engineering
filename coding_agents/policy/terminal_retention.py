from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ESCALATED = "escalated"
    BUDGET_EXHAUSTED = (
        "budget_exhausted"
    )
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class MutationState:
    has_diff: bool
    verified: bool
    external_side_effects: bool


@dataclass(frozen=True)
class RetentionPlan:
    retain_worktree: bool
    retain_patch: bool
    retain_checkpoint: bool
    queue_review: bool
    cleanup_mode: str


def retention_plan(
    outcome: Outcome,
    mutation: MutationState,
) -> RetentionPlan:
    if outcome == Outcome.SUCCEEDED:
        return RetentionPlan(
            retain_worktree=True,
            retain_patch=True,
            retain_checkpoint=True,
            queue_review=False,
            cleanup_mode="open_pr",
        )

    if outcome == Outcome.ESCALATED:
        return RetentionPlan(
            retain_worktree=True,
            retain_patch=mutation.has_diff,
            retain_checkpoint=True,
            queue_review=True,
            cleanup_mode="freeze",
        )

    if outcome == Outcome.BUDGET_EXHAUSTED:
        return RetentionPlan(
            retain_worktree=mutation.has_diff,
            retain_patch=mutation.has_diff,
            retain_checkpoint=True,
            queue_review=False,
            cleanup_mode="resume_eligible",
        )

    if outcome == Outcome.CANCELLED:
        if mutation.external_side_effects:
            cleanup_mode = "manual_cleanup"
        elif mutation.has_diff:
            cleanup_mode = "quarantine_diff"
        else:
            cleanup_mode = "delete_worktree"

        return RetentionPlan(
            retain_worktree=mutation.has_diff,
            retain_patch=mutation.has_diff,
            retain_checkpoint=True,
            queue_review=(
                mutation.external_side_effects
            ),
            cleanup_mode=cleanup_mode,
        )

    return RetentionPlan(
        retain_worktree=False,
        retain_patch=mutation.has_diff,
        retain_checkpoint=True,
        queue_review=False,
        cleanup_mode=(
            "discard_or_quarantine"
        ),
    )


cases = (
    (
        Outcome.SUCCEEDED,
        MutationState(
            True,
            True,
            False,
        ),
    ),
    (
        Outcome.ESCALATED,
        MutationState(
            True,
            False,
            False,
        ),
    ),
    (
        Outcome.BUDGET_EXHAUSTED,
        MutationState(
            True,
            False,
            False,
        ),
    ),
    (
        Outcome.CANCELLED,
        MutationState(
            False,
            False,
            False,
        ),
    ),
    (
        Outcome.CANCELLED,
        MutationState(
            True,
            False,
            True,
        ),
    ),
    (
        Outcome.FAILED,
        MutationState(
            True,
            False,
            False,
        ),
    ),
)

for outcome, mutation in cases:
    plan = retention_plan(
        outcome,
        mutation,
    )

    print(
        f"outcome={outcome.value} "
        f"retain_worktree="
        f"{plan.retain_worktree} "
        f"retain_patch={plan.retain_patch} "
        f"retain_checkpoint="
        f"{plan.retain_checkpoint} "
        f"review={plan.queue_review} "
        f"cleanup={plan.cleanup_mode}"
    )