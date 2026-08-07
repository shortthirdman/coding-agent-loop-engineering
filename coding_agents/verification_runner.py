import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandCheck:
    name: str
    command: tuple[str, ...]
    exit_code: int
    passed: bool
    stdout: str
    stderr: str


def run_check(
    name: str,
    command: tuple[str, ...],
    cwd: Path,
) -> CommandCheck:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    return CommandCheck(
        name=name,
        command=command,
        exit_code=completed.returncode,
        passed=completed.returncode == 0,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
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

    parser.write_text(
        """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}

    for line in block.splitlines():
        if not line.strip():
            continue

        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()

    return headers
""",
        encoding="utf-8",
    )

    test_file.write_text(
        """from src.parser.headers import parse_headers


def test_blank_line_is_ignored() -> None:
    block = "Host: example.com\\n\\nAccept: application/json"

    assert parse_headers(block) == {
        "host": "example.com",
        "accept": "application/json",
    }


def test_standard_headers_are_preserved() -> None:
    block = "Host: example.com\\nAccept: application/json"

    assert parse_headers(block) == {
        "host": "example.com",
        "accept": "application/json",
    }
""",
        encoding="utf-8",
    )

    checks = (
        run_check(
            "targeted_regression",
            (
                sys.executable,
                "-m",
                "pytest",
                (
                    "tests/parser/test_headers.py"
                    "::test_blank_line_is_ignored"
                ),
                "-q",
            ),
            repo,
        ),
        run_check(
            "parser_regression_suite",
            (
                sys.executable,
                "-m",
                "pytest",
                "tests/parser/test_headers.py",
                "-q",
            ),
            repo,
        ),
        run_check(
            "compileall",
            (
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "src",
            ),
            repo,
        ),
    )

    for check in checks:
        print(
            f"check={check.name} "
            f"exit_code={check.exit_code} "
            f"passed={check.passed}"
        )

    print(
        "all_required_checks_passed="
        f"{all(check.passed for check in checks)}"
    )