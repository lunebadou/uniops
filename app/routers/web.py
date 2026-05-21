from fastapi import APIRouter, Request

from app.clients.docker_client import docker_client
from app.core.templates import templates

router = APIRouter(tags=["Web"])


def _collect_containers_with_stats() -> list[dict]:
    """Récupère la liste des conteneurs avec leurs stats (utilisé par dashboard et fragment)."""
    containers = docker_client.list_containers()
    stats = []
    for c in containers:
        try:
            stats.append(docker_client.get_container_stats(c["name"]))
        except Exception:
            stats.append({
                "container_name": c["name"],
                "status": c["status"],
                "cpu_percent": 0,
                "memory_mb": 0,
                "memory_limit_mb": 0,
            })
    return stats


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"containers": _collect_containers_with_stats()},
    )


@router.get("/fragments/cards")
def cards_fragment(request: Request):
    """Fragment HTML rafraîchi automatiquement par HTMX toutes les 5s."""
    return templates.TemplateResponse(
        request,
        "_cards_fragment.html",
        {"containers": _collect_containers_with_stats()},
    )