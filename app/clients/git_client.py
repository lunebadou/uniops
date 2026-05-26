"""
Client Git — encapsule GitPython pour cloner / mettre à jour des dépôts publics.
"""
import shutil
from pathlib import Path
from git import Repo


WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)


def clone_or_update(git_repo: str, branch: str = "main") -> Path:
    """
    Clone le repo si absent, sinon fetch + checkout.
    git_repo : 'owner/repo' (ex: 'lunebadou/supply-chain-app')
    Renvoie le chemin local du dépôt.
    """
    url = f"https://github.com/{git_repo}.git"
    # Le nom de dossier local est dérivé du repo
    folder_name = git_repo.replace("/", "__")
    local_path = WORKSPACE / folder_name

    if local_path.exists():
        # Nettoyer pour repartir d'un état propre (évite les conflits)
        shutil.rmtree(local_path)

    Repo.clone_from(url, local_path, branch=branch, depth=1)
    return local_path