from dataclasses import dataclass
from enum import Enum


class FailureClass(str, Enum):
    TRANSIENT_INFRASTRUCTURE = (
        "transient_infrastructure"
    )
    INVALID_TOOL_REQUEST = (
        "invalid_tool_request"
    )
    FAILED_HYPOTHESIS = "failed_hypothesis"
    VERIFICATION_FAILURE = (
        "verification_failure"
    )
    PERMISSION_BLOCK = "permission_block"
    ENVIRONMENT_MISMATCH = (
        "environment_mismatch"
    )
    NO_PROGRESS = "no_progress"


class RecoveryAction(str, Enum):
    RETRY_SAME_CALL = "retry_same_call"
    RETRY_MODIFIED_CALL = (
        "retry_modified_call"
    )
    REPLAN = "replan"
    ROLLBACK = "rollback"
    ESCALATE = "escalate"
    FAIL = "fail"


@dataclass(frozen=True)
class RecoveryContext:
    failure_class: FailureClass
    retry_count: int
    retry_limit: int
    repository_worsened: bool = False


def choose_recovery(
    context: RecoveryContext,
) -> tuple[RecoveryAction, str]:
    if (
        context.failure_class
        == FailureClass.PERMISSION_BLOCK
    ):
        return (
            RecoveryAction.ESCALATE,
            "permission_boundary_reached",
        )

    if (
        context.failure_class
        == FailureClass.ENVIRONMENT_MISMATCH
    ):
        return (
            RecoveryAction.ESCALATE,
            "verification_environment_unavailable",
        )

    if context.repository_worsened:
        return (
            RecoveryAction.ROLLBACK,
            "candidate_regressed_repository_state",
        )

    if (
        context.failure_class
        == FailureClass.TRANSIENT_INFRASTRUCTURE
    ):
        if context.retry_count < context.retry_limit:
            return (
                RecoveryAction.RETRY_SAME_CALL,
                "transient_failure_with_budget",
            )

        return (
            RecoveryAction.FAIL,
            "transient_retry_budget_exhausted",
        )

    if (
        context.failure_class
        == FailureClass.INVALID_TOOL_REQUEST
    ):
        return (
            RecoveryAction.RETRY_MODIFIED_CALL,
            "repair_tool_arguments",
        )

    if context.failure_class in {
        FailureClass.FAILED_HYPOTHESIS,
        FailureClass.VERIFICATION_FAILURE,
        FailureClass.NO_PROGRESS,
    }:
        return (
            RecoveryAction.REPLAN,
            "new_hypothesis_required",
        )

    return (
        RecoveryAction.FAIL,
        "unhandled_failure_class",
    )


cases = {
    "timeout_first_attempt": RecoveryContext(
        FailureClass.TRANSIENT_INFRASTRUCTURE,
        retry_count=0,
        retry_limit=2,
    ),
    "timeout_budget_spent": RecoveryContext(
        FailureClass.TRANSIENT_INFRASTRUCTURE,
        retry_count=2,
        retry_limit=2,
    ),
    "bad_arguments": RecoveryContext(
        FailureClass.INVALID_TOOL_REQUEST,
        retry_count=0,
        retry_limit=2,
    ),
    "same_parser_failure": RecoveryContext(
        FailureClass.FAILED_HYPOTHESIS,
        retry_count=0,
        retry_limit=2,
    ),
    "regression_detected": RecoveryContext(
        FailureClass.VERIFICATION_FAILURE,
        retry_count=0,
        retry_limit=2,
        repository_worsened=True,
    ),
    "protected_path": RecoveryContext(
        FailureClass.PERMISSION_BLOCK,
        retry_count=0,
        retry_limit=2,
    ),
}

for name, context in cases.items():
    action, reason = choose_recovery(
        context
    )

    print(
        f"case={name} "
        f"action={action.value} "
        f"reason={reason}"
    )