import json
import sys
import tempfile
from pathlib import Path

from coding_agents.evidence_collector import run_git, collect_diff
from coding_agents.provider_result import normalize_claude, normalize_codex
from coding_agents.runner import run_process


def initialize_repo(repo: Path) -> None:
    parser = repo / "src/parser/headers.py"
    test_file = (
        repo
        / "tests/parser/test_headers.py"
    )

    parser.parent.mkdir(parents=True)
    test_file.parent.mkdir(parents=True)

    parser.write_text(
        """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
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
""",
        encoding="utf-8",
    )

    run_git(repo, "init", "-q")
    run_git(
        repo,
        "config",
        "user.email",
        "agent@example.com",
    )
    run_git(
        repo,
        "config",
        "user.name",
        "Agent Test",
    )
    run_git(repo, "add", ".")
    run_git(
        repo,
        "commit",
        "-qm",
        "baseline",
    )


def write_fixture_worker(path: Path) -> None:
    path.write_text(
        '''import json
import sys
from pathlib import Path

provider = sys.argv[1]
repo = Path(sys.argv[2])
parser = repo / "src/parser/headers.py"

text = parser.read_text(encoding="utf-8")
text = text.replace(
    "    for line in block.splitlines():\\n"
    "        name, value = line.split(\\":\\", 1)\\n",
    "    for line in block.splitlines():\\n"
    "        if not line.strip():\\n"
    "            continue\\n"
    "        name, value = line.split(\\":\\", 1)\\n",
)
parser.write_text(text, encoding="utf-8")

if provider == "claude":
    events = [
        {
            "type": "system",
            "subtype": "init",
            "session_id":
                "claude-session-1842",
        },
        {
            "type": "result",
            "subtype": "success",
            "session_id":
                "claude-session-1842",
            "result": (
                "Updated the parser to "
                "skip blank lines."
            ),
        },
    ]
else:
    events = [
        {
            "type": "thread.started",
            "thread_id":
                "codex-thread-7331",
        },
        {
            "type": "item.completed",
            "item": {
                "type": "file_change",
                "path":
                    "src/parser/headers.py",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": (
                    "Updated the parser to "
                    "skip blank lines."
                ),
            },
        },
        {
            "type": "turn.completed",
            "usage": {},
        },
    ]

for event in events:
    print(json.dumps(event), flush=True)
''',
        encoding="utf-8",
    )


with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    fixture_worker = (
        root / "fixture_worker.py"
    )
    write_fixture_worker(fixture_worker)

    for provider in ("claude", "codex"):
        repo = root / provider
        repo.mkdir()
        initialize_repo(repo)

        process = run_process(
            [
                sys.executable,
                str(fixture_worker),
                provider,
                str(repo),
            ],
            cwd=repo,
            timeout_seconds=5.0,
        )

        evidence = collect_diff(repo)

        if provider == "claude":
            result = normalize_claude(
                process.stdout
            )
        else:
            result = normalize_codex(
                process.stdout
            )

        approved_files = {
            "src/parser/headers.py"
        }
        diff_allowed = (
            set(evidence.changed_files)
            <= approved_files
        )

        next_transition = (
            "verify"
            if (
                process.exit_code == 0
                and not process.timed_out
                and diff_allowed
            )
            else "escalate"
        )

        print(
            f"provider={result.provider} "
            f"session={result.session_handle} "
            f"exit_code={process.exit_code}"
        )
        print(
            "changed_files="
            + ",".join(
                evidence.changed_files
            )
        )
        print(
            f"diff_allowed={diff_allowed}"
        )
        print(
            "native_stop="
            f"{result.native_stop_reason}"
        )
        print(
            "next_transition="
            f"{next_transition}"
        )