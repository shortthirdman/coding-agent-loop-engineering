import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HistoricalCheck:
    implementation: str
    exit_code: int
    passed: bool
    failure_contains_original_fingerprint: bool


def run_targeted_test(repo: Path) -> HistoricalCheck:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            (
                "tests/parser/test_headers.py"
                "::test_blank_line_is_ignored"
            ),
            "-q",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout

    return HistoricalCheck(
        implementation="current",
        exit_code=completed.returncode,
        passed=completed.returncode == 0,
        failure_contains_original_fingerprint=(
            "not enough values to unpack" in output
        ),
    )


with tempfile.TemporaryDirectory() as temp_dir:
    repo = Path(temp_dir)
    parser = repo / "src/parser/headers.py"
    test_file = repo / "tests/parser/test_headers.py"

    parser.parent.mkdir(parents=True)
    test_file.parent.mkdir(parents=True)

    (repo / "src/__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (repo / "src/parser/__init__.py").write_text(
        "",
        encoding="utf-8",
    )

    fixed_source = """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        if not line.strip():
            continue

        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers
"""

    original_source = """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers
"""

    test_file.write_text(
        """from src.parser.headers import parse_headers


def test_blank_line_is_ignored() -> None:
    block = "Host: example.com\\n\\nAccept: application/json"

    assert parse_headers(block) == {
        "host": "example.com",
        "accept": "application/json",
    }
""",
        encoding="utf-8",
    )

    parser.write_text(
        fixed_source,
        encoding="utf-8",
    )
    fixed = run_targeted_test(repo)

    parser.write_text(
        original_source,
        encoding="utf-8",
    )
    original = run_targeted_test(repo)

    print(
        f"fixed_version_passed={fixed.passed} "
        f"exit_code={fixed.exit_code}"
    )
    print(
        f"original_version_passed={original.passed} "
        f"exit_code={original.exit_code}"
    )
    print(
        "original_failure_matches_fingerprint="
        f"{original.failure_contains_original_fingerprint}"
    )
    print(
        "regression_test_proves_patch="
        f"{fixed.passed and not original.passed}"
    )