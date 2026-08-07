from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    evidence_ref: str


@dataclass(frozen=True)
class VerificationBundle:
    patch_sha256: str
    changed_files: tuple[str, ...]
    approved_files: tuple[str, ...]
    checks: tuple[CheckResult, ...]
    regression_test_proves_patch: bool


@dataclass(frozen=True)
class VerificationDecision:
    outcome: Literal[
        "accept",
        "retry",
        "replan",
        "rollback",
        "escalate",
    ]
    reason: str


def verify_bundle(
    bundle: VerificationBundle,
) -> VerificationDecision:
    unexpected = (
        set(bundle.changed_files)
        - set(bundle.approved_files)
    )

    if unexpected:
        return VerificationDecision(
            outcome="escalate",
            reason=(
                "unexpected_files:"
                + ",".join(sorted(unexpected))
            ),
        )

    failed = [
        check.name
        for check in bundle.checks
        if not check.passed
    ]

    if failed:
        return VerificationDecision(
            outcome="replan",
            reason=(
                "failed_checks:"
                + ",".join(failed)
            ),
        )

    if not bundle.regression_test_proves_patch:
        return VerificationDecision(
            outcome="retry",
            reason="regression_test_not_discriminating",
        )

    return VerificationDecision(
        outcome="accept",
        reason=(
            "scope_valid_and_all_required_"
            "evidence_passed"
        ),
    )


bundles = {
    "accepted": VerificationBundle(
        patch_sha256="f539017f38a4cd3b",
        changed_files=(
            "src/parser/headers.py",
        ),
        approved_files=(
            "src/parser/headers.py",
        ),
        checks=(
            CheckResult(
                "targeted_regression",
                True,
                "artifacts/pytest-targeted.txt",
            ),
            CheckResult(
                "parser_regression_suite",
                True,
                "artifacts/pytest-parser.txt",
            ),
            CheckResult(
                "compileall",
                True,
                "artifacts/compileall.txt",
            ),
        ),
        regression_test_proves_patch=True,
    ),
    "unexpected_file": VerificationBundle(
        patch_sha256="4b32f102c183a988",
        changed_files=(
            "src/parser/headers.py",
            "README.md",
        ),
        approved_files=(
            "src/parser/headers.py",
        ),
        checks=(
            CheckResult(
                "targeted_regression",
                True,
                "artifacts/pytest-targeted.txt",
            ),
        ),
        regression_test_proves_patch=True,
    ),
}

for name, bundle in bundles.items():
    decision = verify_bundle(bundle)

    print(
        f"bundle={name} "
        f"outcome={decision.outcome} "
        f"reason={decision.reason}"
    )