"""Run hassfest against a clean copy of the working tree."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HASSFEST_IMAGE = "ghcr.io/home-assistant/hassfest"


def _git_files() -> list[Path]:
    """Return tracked and untracked non-ignored files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [REPO_ROOT / path.decode() for path in result.stdout.split(b"\0") if path]


def _copy_worktree(target: Path) -> None:
    """Copy the current relevant working tree into a temporary directory."""
    for source in _git_files():
        if not source.is_file():
            continue
        destination = target / source.relative_to(REPO_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    """Run the hassfest Docker image against a clean workspace."""
    with tempfile.TemporaryDirectory(prefix="ha-smd-key-hassfest-") as tmp_dir:
        workspace = Path(tmp_dir)
        _copy_worktree(workspace)
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{workspace}:/github/workspace",
                HASSFEST_IMAGE,
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
