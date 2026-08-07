from dataclasses import dataclass, field
from hashlib import sha256


@dataclass(frozen=True)
class Attempt:
    action: str
    normalized_input: str
    failure_signature: str


def failure_fingerprint(
    attempt: Attempt,
) -> str:
    payload = "|".join(
        (
            attempt.action,
            attempt.normalized_input,
            attempt.failure_signature,
        )
    )

    return sha256(
        payload.encode("utf-8")
    ).hexdigest()[:12]


@dataclass
class RetryLedger:
    per_fingerprint_limit: int
    counts: dict[str, int] = field(
        default_factory=dict
    )

    def record(
        self,
        fingerprint: str,
    ) -> int:
        self.counts[fingerprint] = (
            self.counts.get(fingerprint, 0) + 1
        )
        return self.counts[fingerprint]

    def can_retry(
        self,
        fingerprint: str,
    ) -> bool:
        return (
            self.counts.get(fingerprint, 0)
            < self.per_fingerprint_limit
        )


ledger = RetryLedger(
    per_fingerprint_limit=2
)

attempts = (
    Attempt(
        action="patch_parser",
        normalized_input="strip line before split",
        failure_signature=(
            "ValueError:not enough values to unpack"
        ),
    ),
    Attempt(
        action="patch_parser",
        normalized_input="strip line before split",
        failure_signature=(
            "ValueError:not enough values to unpack"
        ),
    ),
    Attempt(
        action="patch_parser",
        normalized_input="skip empty line before split",
        failure_signature=(
            "ValueError:not enough values to unpack"
        ),
    ),
)

for attempt in attempts:
    fingerprint = failure_fingerprint(
        attempt
    )
    count = ledger.record(fingerprint)

    print(
        f"fingerprint={fingerprint} "
        f"count={count} "
        f"can_retry="
        f"{ledger.can_retry(fingerprint)} "
        f"input={attempt.normalized_input}"
    )