"""GitPython helpers."""

from pathlib import Path

from git import Repo


def clone_or_update_repository(repository_url: str, branch: str, target_path: Path) -> Path:
    """Clone a repository or update an existing checkout."""
    if target_path.exists():
        repo = Repo(target_path)
        repo.git.fetch("--all", "--prune")
        repo.git.checkout(branch)
        repo.git.pull("origin", branch)
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    Repo.clone_from(repository_url, target_path, branch=branch, depth=1)
    return target_path


__all__ = ["clone_or_update_repository"]
