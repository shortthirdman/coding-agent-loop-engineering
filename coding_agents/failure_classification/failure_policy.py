from dataclasses import dataclass
from enum import Enum
from typing import Literal


class FailureClass(str, Enum):
    TRANSIENT_INFRASTRUCTURE = "transient_infrastructure"
    INVALID_TOOL_REQUEST = "invalid_tool_request"
    FAILED_HYPOTHESIS = "failed_hypothesis"
    VERIFICATION_FAILURE = "verification_failure"
    PERMISSION_BLOCK = "permission_block"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    NO_PROGRESS = "no_progress"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureEvidence:
    source: Literal[
        "process",
        "tool",
        "verification",
        "policy",
        "progress",
    ]
    exit_code: int | None = None
    timed_out: bool = False
    error_code: str | None = None
    verification_failed: bool = False
    same_failure_fingerprint: bool = False
    permission_blocked: bool = False
    environment_missing: bool = False
    progress_delta: int | None = None


def classify_failure(
    evidence: FailureEvidence,
) -> FailureClass:
    if (
        evidence.permission_blocked
        or evidence.source == "policy"
    ):
        return FailureClass.PERMISSION_BLOCK

    if (
        evidence.timed_out
        or evidence.error_code
        in {"rate_limit", "service_unavailable"}
    ):
        return FailureClass.TRANSIENT_INFRASTRUCTURE

    if evidence.error_code in {
        "invalid_arguments",
        "schema_validation",
    }:
        return FailureClass.INVALID_TOOL_REQUEST

    if evidence.environment_missing:
        return FailureClass.ENVIRONMENT_MISMATCH

    if (
        evidence.source == "verification"
        and evidence.verification_failed
    ):
        if evidence.same_failure_fingerprint:
            return FailureClass.FAILED_HYPOTHESIS

        return FailureClass.VERIFICATION_FAILURE

    if (
        evidence.source == "progress"
        and (evidence.progress_delta or 0) <= 0
    ):
        return FailureClass.NO_PROGRESS

    return FailureClass.UNKNOWN


cases = {
    "api_timeout": FailureEvidence(
        source="process",
        timed_out=True,
    ),
    "bad_tool_args": FailureEvidence(
        source="tool",
        error_code="invalid_arguments",
    ),
    "same_parser_failure": FailureEvidence(
        source="verification",
        verification_failed=True,
        same_failure_fingerprint=True,
    ),
    "new_regression": FailureEvidence(
        source="verification",
        verification_failed=True,
        same_failure_fingerprint=False,
    ),
    "protected_path": FailureEvidence(
        source="policy",
        permission_blocked=True,
    ),
}

for name, evidence in cases.items():
    print(
        f"case={name} "
        f"class={classify_failure(evidence).value}"
    )