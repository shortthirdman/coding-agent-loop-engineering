from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class ProgressSnapshot:
    failing_tests: int
    completed_steps: int
    failure_fingerprint: str
    diff_sha256: str


def compare_progress(
    previous: ProgressSnapshot,
    current: ProgressSnapshot,
) -> int:
    score = 0

    score += (
        previous.failing_tests
        - current.failing_tests
    )
    score += (
        current.completed_steps
        - previous.completed_steps
    )

    if (
        current.failure_fingerprint
        != previous.failure_fingerprint
    ):
        score += 1

    if (
        current.diff_sha256
        != previous.diff_sha256
    ):
        score += 1

    return score


def state_fingerprint(
    snapshot: ProgressSnapshot,
) -> str:
    payload = (
        f"{snapshot.failing_tests}|"
        f"{snapshot.completed_steps}|"
        f"{snapshot.failure_fingerprint}|"
        f"{snapshot.diff_sha256}"
    )

    return sha256(
        payload.encode("utf-8")
    ).hexdigest()[:12]


history = [
    ProgressSnapshot(
        1,
        3,
        "valueerror-blank-line",
        "patch-a",
    ),
    ProgressSnapshot(
        1,
        3,
        "valueerror-blank-line",
        "patch-a",
    ),
    ProgressSnapshot(
        1,
        3,
        "valueerror-blank-line",
        "patch-b",
    ),
    ProgressSnapshot(
        0,
        5,
        "none",
        "patch-c",
    ),
]

seen: dict[str, int] = {}

for index, snapshot in enumerate(history):
    fingerprint = state_fingerprint(
        snapshot
    )
    seen[fingerprint] = (
        seen.get(fingerprint, 0) + 1
    )

    delta = (
        0
        if index == 0
        else compare_progress(
            history[index - 1],
            snapshot,
        )
    )

    print(
        f"iteration={index + 1} "
        f"progress_delta={delta} "
        f"state_repeat_count="
        f"{seen[fingerprint]} "
        f"fingerprint={fingerprint}"
    )