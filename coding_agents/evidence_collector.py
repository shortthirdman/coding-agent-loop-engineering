import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiffEvidence:
    changed_files: tuple[str, ...]
    additions: int
    deletions: int
    patch_sha256: str


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return completed.stdout


def collect_diff(repo: Path) -> DiffEvidence:
    changed_files = tuple(
        line
        for line in run_git(
            repo,
            "diff",
            "--name-only",
        ).splitlines()
        if line
    )

    additions = 0
    deletions = 0

    for line in run_git(
        repo,
        "diff",
        "--numstat",
    ).splitlines():
        added, deleted, _path = line.split(
            "\t",
            2,
        )
        additions += int(added)
        deletions += int(deleted)

    patch = run_git(
        repo,
        "diff",
        "--binary",
    )

    return DiffEvidence(
        changed_files=changed_files,
        additions=additions,
        deletions=deletions,
        patch_sha256=hashlib.sha256(
            patch.encode("utf-8")
        ).hexdigest(),
    )


with tempfile.TemporaryDirectory() as temp_dir:
    repo = Path(temp_dir)
    source = repo / "src/parser/headers.py"
    source.parent.mkdir(parents=True)

    source.write_text(
        """def parse_headers(block: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in block.splitlines():
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    return headers
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

    source.write_text(
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

    evidence = collect_diff(repo)
    approved_files = {
        "src/parser/headers.py"
    }
    unexpected = sorted(
        set(evidence.changed_files)
        - approved_files
    )

    print(
        "changed_files="
        + ",".join(evidence.changed_files)
    )
    print(f"additions={evidence.additions}")
    print(f"deletions={evidence.deletions}")
    print(
        "unexpected_files="
        f"{','.join(unexpected) or 'none'}"
    )
    print(
        "patch_sha256="
        f"{evidence.patch_sha256[:16]}"
    )