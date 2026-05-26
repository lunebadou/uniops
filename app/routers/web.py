from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session

from app.clients.docker_client import docker_client
from app.core.templates import templates
from app.database import get_db
from app.repositories import metric_repository, anomaly_repository

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


def _serialize_anomalies(items) -> list[dict]:
    """Sérialise les anomalies pour le template, avec dates formatées en français."""
    return [
        {
            "id": a.id,
            "container_name": a.container_name,
            "type": a.type.value,
            "severity": a.severity.value,
            "observed_value": a.observed_value,
            "threshold_value": a.threshold_value,
            "duration_points": a.duration_points,
            "ai_analysis": a.ai_analysis,
            "detected_at_fmt": a.detected_at.strftime("%d/%m/%Y %H:%M:%S"),
            "resolved": a.resolved,
            "resolved_at_fmt": a.resolved_at.strftime("%d/%m/%Y %H:%M:%S") if a.resolved_at else None,
        }
        for a in items
    ]


# ───── Dashboard ─────
@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "containers": _collect_containers_with_stats(),
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )


@router.get("/fragments/cards")
def cards_fragment(request: Request):
    return templates.TemplateResponse(
        request,
        "_cards_fragment.html",
        {"containers": _collect_containers_with_stats()},
    )


# ───── Page détail conteneur ─────
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
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )


# ───── Page anomalies ─────
@router.get("/anomalies")
def anomalies_page(
    request: Request,
    only_unresolved: bool = False,
    db: Session = Depends(get_db),
):
    items = anomaly_repository.get_all(db, only_unresolved=only_unresolved)
    return templates.TemplateResponse(
        request,
        "anomalies.html",
        {
            "anomalies": _serialize_anomalies(items),
            "only_unresolved": only_unresolved,
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )


@router.get("/fragments/anomalies")
def anomalies_fragment(
    request: Request,
    only_unresolved: bool = False,
    db: Session = Depends(get_db),
):
    items = anomaly_repository.get_all(db, only_unresolved=only_unresolved)
    return templates.TemplateResponse(
        request,
        "_anomalies_fragment.html",
        {"anomalies": _serialize_anomalies(items)},
    )


# ───── Cloche en header (compteur) ─────
@router.get("/fragments/anomaly-bell")
def anomaly_bell_fragment(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "_bell_fragment.html",
        {"open_anomalies": anomaly_repository.count_unresolved(db)},
    )