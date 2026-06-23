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

from app.repositories import pipeline_repository

_STATUS_LABELS = {
    "pending": "En attente",
    "running": "En cours",
    "success": "Succès",
    "failed": "Échec",
    "awaiting_validation": "Validation requise",
    "rejected": "Refusé",
}


def _serialize_pipeline(p) -> dict:
    return {
        "id": p.id,
        "application_name": p.application_name,
        "git_repo": p.git_repo,
        "git_branch": p.git_branch,
        "environment": p.environment,
        "status": p.status.value,
        "status_label": _STATUS_LABELS.get(p.status.value, p.status.value),
        "human_validated": p.human_validated,
        "started_at_fmt": p.started_at.strftime("%d/%m/%Y %H:%M:%S") if p.started_at else None,
        "finished_at_fmt": p.finished_at.strftime("%d/%m/%Y %H:%M:%S") if p.finished_at else None,
        "steps": [
            {
                "id": s.id,
                "name": s.name,
                "order": s.order,
                "status": s.status.value,
                "error_message": s.error_message,
            }
            for s in p.steps
        ],
    }

# ───── Nouvelle Page Applications (Jobs) ─────
from app.repositories import application_repository

@router.get("/applications")
def applications_page(request: Request, db: Session = Depends(get_db)):
    apps = application_repository.get_all(db)
    return templates.TemplateResponse(
        request,
        "applications.html",
        {
            "applications": apps,
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )

# ───── Page Pipelines ─────
@router.get("/pipelines")
def pipelines_page(request: Request, db: Session = Depends(get_db)):
    runs = pipeline_repository.list_runs(db)
    return templates.TemplateResponse(
        request,
        "pipelines.html",
        {
            "pipelines": [_serialize_pipeline(r) for r in runs],
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )


@router.get("/fragments/pipelines")
def pipelines_fragment(request: Request, db: Session = Depends(get_db)):
    runs = pipeline_repository.list_runs(db)
    return templates.TemplateResponse(
        request,
        "_pipelines_fragment.html",
        {"pipelines": [_serialize_pipeline(r) for r in runs]},
    )


@router.get("/pipelines/{run_id}")
def pipeline_detail_page(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = pipeline_repository.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline introuvable")
    return templates.TemplateResponse(
        request,
        "pipeline_detail.html",
        {
            "pipeline": _serialize_pipeline(run),
            "open_anomalies": anomaly_repository.count_unresolved(db),
        },
    )

@router.get("/pipelines/{run_id}/steps-fragment")
def pipeline_steps_fragment(run_id: int, request: Request, db: Session = Depends(get_db)):
    run = pipeline_repository.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline introuvable")
    steps = [
        {
            "id": s.id,
            "name": s.name,
            "order": s.order,
            "status": s.status.value,
            "output": s.output,
            "error_message": s.error_message,
        }
        for s in run.steps
    ]
    return templates.TemplateResponse(
        request,
        "_pipeline_steps_fragment.html",
        {"steps": steps},
    )