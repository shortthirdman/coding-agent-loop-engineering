import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def _merge_output(prefix: str, suffix: str) -> str:
    if not prefix:
        return suffix

    if suffix.startswith(prefix):
        return suffix

    return prefix + suffix

def run_process(
    command: list[str],
    cwd: Path,
    timeout_seconds: float,
) -> ProcessResult:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(
            timeout=timeout_seconds
        )

        return ProcessResult(
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )

    except subprocess.TimeoutExpired as exc:
        partial_stdout = _as_text(exc.stdout)
        partial_stderr = _as_text(exc.stderr)

        os.killpg(process.pid, signal.SIGTERM)

        try:
            tail_stdout, tail_stderr = process.communicate(
                timeout=1.0
            )
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            tail_stdout, tail_stderr = process.communicate(
                timeout=1.0
            )

        return ProcessResult(
            exit_code=process.returncode,
            stdout=_merge_output(
                partial_stdout,
                tail_stdout,
            ),
            stderr=_merge_output(
                partial_stderr,
                tail_stderr,
            ),
            timed_out=True,
        )

with tempfile.TemporaryDirectory() as temp_dir:
    workdir = Path(temp_dir)
    worker = workdir / "fixture_worker.py"

    worker.write_text(
        """import json
import sys
import time

mode = sys.argv[1]
print(
    json.dumps({"type": "turn.started"}),
    flush=True,
)

if mode == "timeout":
    time.sleep(5)
else:
    print(
        json.dumps({"type": "turn.completed"}),
        flush=True,
    )
""",
        encoding="utf-8",
    )

    completed = run_process(
        [
            sys.executable,
            str(worker),
            "complete",
        ],
        cwd=workdir,
        timeout_seconds=2.0,
    )

    timed_out = run_process(
        [
            sys.executable,
            str(worker),
            "timeout",
        ],
        cwd=workdir,
        timeout_seconds=0.5,
    )

    for label, result in (
            ("completed", completed),
            ("timed_out", timed_out),
    ):
        output_lines = (
            result.stdout.strip().splitlines()
        )

        print(
            f"case={label} "
            f"exit_code={result.exit_code} "
            f"timed_out={result.timed_out} "
            f"stdout_lines={len(output_lines)}"
        )