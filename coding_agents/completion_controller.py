from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CompletionState:
    verification_outcome: str
    all_required_predicates_passed: bool
    unresolved_plan_steps: int
    remaining_budget: bool
    human_approval_required: bool


@dataclass(frozen=True)
class CompletionDecision:
    transition: Literal[
        "succeed",
        "replan",
        "escalate",
        "fail",
    ]
    reason: str


def decide_completion(
    state: CompletionState,
) -> CompletionDecision:
    if state.human_approval_required:
        return CompletionDecision(
            "escalate",
            "human_approval_required",
        )

    if not state.remaining_budget:
        return CompletionDecision(
            "fail",
            "outer_budget_exhausted",
        )

    if state.verification_outcome != "accept":
        return CompletionDecision(
            "replan",
            (
                "verification_outcome:"
                f"{state.verification_outcome}"
            ),
        )

    if not state.all_required_predicates_passed:
        return CompletionDecision(
            "replan",
            "required_predicate_failed",
        )

    if state.unresolved_plan_steps:
        return CompletionDecision(
            "replan",
            (
                "unresolved_steps:"
                f"{state.unresolved_plan_steps}"
            ),
        )

    return CompletionDecision(
        "succeed",
        "verified_completion",
    )


cases = {
    "parser_patch": CompletionState(
        verification_outcome="accept",
        all_required_predicates_passed=True,
        unresolved_plan_steps=0,
        remaining_budget=True,
        human_approval_required=False,
    ),
    "verification_failed": CompletionState(
        verification_outcome="replan",
        all_required_predicates_passed=False,
        unresolved_plan_steps=1,
        remaining_budget=True,
        human_approval_required=False,
    ),
    "budget_exhausted": CompletionState(
        verification_outcome="replan",
        all_required_predicates_passed=False,
        unresolved_plan_steps=1,
        remaining_budget=False,
        human_approval_required=False,
    ),
}

for name, state in cases.items():
    decision = decide_completion(state)

    print(
        f"case={name} "
        f"transition={decision.transition} "
        f"reason={decision.reason}"
    )