from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Decision(str, Enum):
    REPLAN = "replan"
    SUCCEED = "succeed"


@dataclass(frozen=True)
class AttemptResult:
    name: str
    passed: bool
    failure_fingerprint: str | None
    observation: str


def original_parser(
    block: str,
) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers


def strip_only_parser(
    block: str,
) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        line = line.strip()
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers


def skip_blank_parser(
    block: str,
) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        if not line.strip():
            continue

        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers


def evaluate(
    name: str,
    parser: Callable[
        [str],
        dict[str, str],
    ],
) -> AttemptResult:
    sample = (
        "Host: example.com\n\n"
        "Accept: application/json"
    )
    expected = {
        "host": "example.com",
        "accept": "application/json",
    }

    try:
        result = parser(sample)
    except ValueError as exc:
        return AttemptResult(
            name=name,
            passed=False,
            failure_fingerprint=(
                "ValueError:"
                "not_enough_values_to_unpack"
            ),
            observation=str(exc),
        )

    return AttemptResult(
        name=name,
        passed=result == expected,
        failure_fingerprint=(
            None
            if result == expected
            else "wrong_output"
        ),
        observation=f"parsed={result}",
    )


attempts = (
    evaluate(
        "original",
        original_parser,
    ),
    evaluate(
        "strip_only",
        strip_only_parser,
    ),
    evaluate(
        "skip_blank",
        skip_blank_parser,
    ),
)

previous_fingerprint: str | None = None

for index, result in enumerate(
    attempts,
    start=1,
):
    if result.passed:
        decision = Decision.SUCCEED
        failure_changed = True
    else:
        failure_changed = (
            result.failure_fingerprint
            != previous_fingerprint
        )
        decision = Decision.REPLAN

    print(
        f"attempt={index} "
        f"implementation={result.name} "
        f"passed={result.passed} "
        f"failure_changed={failure_changed} "
        f"decision={decision.value}"
    )

    previous_fingerprint = (
        result.failure_fingerprint
    )