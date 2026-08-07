from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    evidence: str

def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers

def check_blank_line() -> CheckResult:
    sample = "Host: example.com\n\nAccept: application/json"
    try:
        parsed = parse_headers(sample)
    except ValueError as exc:
        return CheckResult(
            "blank_line_is_ignored",
            False,
            f"ValueError:{exc}",
        )
    return CheckResult(
        "blank_line_is_ignored",
        parsed.get("accept") == "application/json",
        f"parsed={parsed}",
    )

def check_standard_headers() -> CheckResult:
    sample = "Host: example.com\nAccept: application/json"
    parsed = parse_headers(sample)
    expected = {
        "host": "example.com",
        "accept": "application/json",
    }
    return CheckResult(
        "standard_headers_preserved",
        parsed == expected,
        f"parsed={parsed}",
    )

def check_regression_test() -> CheckResult:
    discovered_tests = {"test_standard_headers"}
    required = "test_blank_line_is_ignored"
    return CheckResult(
        "regression_test_exists",
        required in discovered_tests,
        f"required={required}",
    )

checks: tuple[Callable[[], CheckResult], ...] = (
    check_blank_line,
    check_standard_headers,
    check_regression_test,
)
results = [check() for check in checks]
for result in results:
    print(
        f"{result.name}:"
        f"passed={result.passed}:"
        f"evidence={result.evidence}"
    )
print(f"task_complete={all(item.passed for item in results)}")