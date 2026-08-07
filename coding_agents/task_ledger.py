from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Budget:
    max_iterations: int
    max_seconds: float
    max_cost_usd: float
    max_changed_files: int


@dataclass(frozen=True)
class Usage:
    iterations: int = 0
    seconds: float = 0.0
    cost_usd: float = 0.0
    changed_files: int = 0


@dataclass(frozen=True)
class Reservation:
    seconds: float
    cost_usd: float
    changed_files: int


def remaining(
    budget: Budget,
    usage: Usage,
) -> dict[str, float | int]:
    return {
        "iterations": (
            budget.max_iterations
            - usage.iterations
        ),
        "seconds": round(
            budget.max_seconds
            - usage.seconds,
            2,
        ),
        "cost_usd": round(
            budget.max_cost_usd
            - usage.cost_usd,
            2,
        ),
        "changed_files": (
            budget.max_changed_files
            - usage.changed_files
        ),
    }


def can_reserve(
    budget: Budget,
    usage: Usage,
    reservation: Reservation,
) -> tuple[bool, str]:
    capacity = remaining(
        budget,
        usage,
    )

    requirements = {
        "iterations": 1,
        "seconds": reservation.seconds,
        "cost_usd": reservation.cost_usd,
        "changed_files": (
            reservation.changed_files
        ),
    }

    for name, required in requirements.items():
        if capacity[name] < required:
            return (
                False,
                f"{name}_insufficient",
            )

    return True, "budget_reserved"


def charge(
    usage: Usage,
    actual: Reservation,
) -> Usage:
    return replace(
        usage,
        iterations=usage.iterations + 1,
        seconds=(
            usage.seconds + actual.seconds
        ),
        cost_usd=(
            usage.cost_usd + actual.cost_usd
        ),
        changed_files=max(
            usage.changed_files,
            actual.changed_files,
        ),
    )


budget = Budget(
    max_iterations=3,
    max_seconds=120.0,
    max_cost_usd=5.00,
    max_changed_files=4,
)
usage = Usage()

reservations = (
    Reservation(30.0, 1.50, 1),
    Reservation(45.0, 1.50, 2),
    Reservation(30.0, 1.00, 2),
    Reservation(10.0, 0.50, 1),
)

actuals = (
    Reservation(18.4, 0.72, 1),
    Reservation(31.6, 1.18, 2),
    Reservation(22.0, 0.81, 2),
)

for index, reservation in enumerate(
    reservations,
    start=1,
):
    allowed, reason = can_reserve(
        budget,
        usage,
        reservation,
    )

    print(
        f"before_iteration={index} "
        f"allowed={allowed} "
        f"reason={reason} "
        f"remaining={remaining(budget, usage)}"
    )

    if allowed and index <= len(actuals):
        usage = charge(
            usage,
            actuals[index - 1],
        )