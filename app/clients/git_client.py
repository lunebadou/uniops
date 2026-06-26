"""
Client Git — encapsule GitPython pour cloner / mettre à jour des dépôts publics.
"""
import shutil
from pathlib import Path
from git import Repo


WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)


def _normalize_git_repo(git_repo: str) -> str:
    """Accepte owner/repo ou URL GitHub complète et renvoie owner/repo."""
    repo = git_repo.strip()
    if repo.endswith(".git"):
        repo = repo[:-4]
    repo = repo.rstrip("/")

    if repo.startswith("git@github.com:"):
        return repo[len("git@github.com:") :]
    if repo.startswith("https://github.com/"):
        return repo[len("https://github.com/") :]
    if repo.startswith("http://github.com/"):
        return repo[len("http://github.com/") :]

    return repo


def clone_or_update(git_repo: str, branch: str = "main") -> Path:
    """
    Clone le repo si absent, sinon supprime et reclone proprement.
    git_repo peut être soit owner/repo, soit une URL GitHub complète.
    Renvoie le chemin local du dépôt.
    """
    normalized_repo = _normalize_git_repo(git_repo)
    url = f"https://github.com/{normalized_repo}.git"
    folder_name = normalized_repo.replace("/", "__")
    local_path = WORKSPACE / folder_name

    if local_path.exists():
        shutil.rmtree(local_path)

    Repo.clone_from(url, local_path, branch=branch, depth=1)
    return local_path.resolve()
