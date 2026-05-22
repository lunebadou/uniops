from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session

from app.clients.docker_client import docker_client
from app.core.templates import templates
from app.database import get_db
from app.repositories import metric_repository

router = APIRouter(tags=["Web"])


def _collect_containers_with_stats() -> list[dict]:
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
    return templates.TemplateResponse(
        request,
        "_cards_fragment.html",
        {"containers": _collect_containers_with_stats()},
    )


@router.get("/containers/{container_name}")
def container_detail(
    container_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        stats = docker_client.get_container_stats(container_name)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conteneur introuvable")

    history = metric_repository.get_history(db, container_name, minutes=60)

    return templates.TemplateResponse(
        request,
        "container_detail.html",
        {
            "container": stats,
            "history_count": len(history),
        },
    )