import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeAllocation:
    branch: str
    path: Path
    base_commit: str


def run_git(
    repo: Path,
    *args: str,
) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return completed.stdout.strip()


def allocate_worktree(
    repository: Path,
    worktree_path: Path,
    branch: str,
) -> WorktreeAllocation:
    base_commit = run_git(
        repository,
        "rev-parse",
        "HEAD",
    )

    run_git(
        repository,
        "worktree",
        "add",
        "-q",
        "-b",
        branch,
        str(worktree_path),
        base_commit,
    )

    return WorktreeAllocation(
        branch=branch,
        path=worktree_path,
        base_commit=base_commit,
    )


with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    repository = root / "repository"
    repository.mkdir()

    parser = repository / "parser.py"
    parser.write_text(
        "VALUE = 'baseline'\n",
        encoding="utf-8",
    )

    run_git(repository, "init", "-q")
    run_git(
        repository,
        "config",
        "user.email",
        "agent@example.com",
    )
    run_git(
        repository,
        "config",
        "user.name",
        "Agent Test",
    )
    run_git(repository, "add", ".")
    run_git(
        repository,
        "commit",
        "-qm",
        "baseline",
    )

    allocation = allocate_worktree(
        repository=repository,
        worktree_path=root / "parser-fix",
        branch="agent/parser-fix",
    )

    worktree_parser = (
        allocation.path / "parser.py"
    )
    worktree_parser.write_text(
        "VALUE = 'candidate'\n",
        encoding="utf-8",
    )

    print(
        "main_value="
        f"{parser.read_text().strip()}"
    )
    print(
        "worktree_value="
        f"{worktree_parser.read_text().strip()}"
    )
    print(
        "worktree_branch="
        f"{run_git(allocation.path, 'branch', '--show-current')}"
    )
    print(
        "main_changed="
        f"{run_git(repository, 'status', '--porcelain') or 'none'}"
    )
    print(
        "worktree_changed="
        f"{run_git(allocation.path, 'status', '--porcelain') or 'none'}"
    )