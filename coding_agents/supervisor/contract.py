from dataclasses import dataclass

@dataclass(frozen=True)
class AcceptanceCriterion:
    name: str
    command: str

@dataclass(frozen=True)
class LoopContract:
    objective: str
    writable_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    criteria: tuple[AcceptanceCriterion, ...]
    max_outer_iterations: int
    max_changed_files: int

def validate_contract(contract: LoopContract) -> list[str]:
    errors: list[str] = []
    if not contract.objective.strip():
        errors.append("objective_empty")
    if not contract.writable_paths:
        errors.append("writable_paths_empty")
    if not contract.criteria:
        errors.append("criteria_empty")
    if contract.max_outer_iterations < 1:
        errors.append("invalid_iteration_limit")
    return errors

def render_shared_guidance(contract: LoopContract) -> str:
    checks = "\n".join(
        f"- `{item.command}` ({item.name})"
        for item in contract.criteria
    )
    writable = "\n".join(
        f"- `{path}`" for path in contract.writable_paths
    )
    protected = "\n".join(
        f"- `{path}`" for path in contract.protected_paths
    )
    return f"""# Parser maintenance rules
## Objective
{contract.objective}
## Writable scope
{writable}
## Protected scope
{protected}
## Required checks
{checks}
"""

contract = LoopContract(
    objective=(
        "Fix blank-line handling in parse_headers "
        "and add a regression test."
    ),
    writable_paths=(
        "src/parser/**",
        "tests/parser/**",
    ),
    protected_paths=(
        "migrations/**",
        "infrastructure/**",
    ),
    criteria=(
        AcceptanceCriterion(
            "targeted_regression",
            "pytest tests/parser/test_headers.py -q",
        ),
        AcceptanceCriterion(
            "static_analysis",
            "python -m compileall -q src",
        ),
    ),
    max_outer_iterations=4,
    max_changed_files=4,
)
errors = validate_contract(contract)
guidance = render_shared_guidance(contract)
print(f"contract_valid={not errors}")
print(f"outer_iteration_limit={contract.max_outer_iterations}")
print(f"required_checks={len(contract.criteria)}")
print("guidance_preview=")
print("\n".join(guidance.splitlines()[:8]))