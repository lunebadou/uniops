from fastapi import APIRouter, Depends, HTTPException, Request, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.templates import templates
from app.database import get_db
from app.repositories import pipeline_repository, application_repository
from app.services import pipeline_service

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])

class PipelineRunCreate(BaseModel):
    application_name: str
    git_repo: str
    git_branch: str = "main"
    environment: str

_STATUS_LABELS = {
    "pending": "En attente",
    "running": "En cours",
    "success": "Succès",
    "failed": "Échec",
    "awaiting_validation": "Validation requise",
    "rejected": "Refusé",
}

def _serialize_step(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "order": s.order,
        "status": s.status.value,
        "output": s.output,
        "error_message": s.error_message,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
    }

def _serialize_run(r) -> dict:
    """Sérialisation expurgée de l'IA pour l'API pure (JSON)"""
    return {
        "id": r.id,
        "application_name": r.application_name,
        "git_repo": r.git_repo,
        "git_branch": r.git_branch,
        "environment": r.environment,
        "status": r.status.value,
        "human_validated": r.human_validated,
        "human_validated_by": r.human_validated_by,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "steps": [_serialize_step(s) for s in r.steps],
    }

def _serialize_pipeline_for_web(p) -> dict:
    """Sérialisation formatée pour l'interface HTMX"""
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
                "output": s.output,           # <- Ajout vital pour afficher les logs !
                "error_message": s.error_message,
            }
            for s in p.steps
        ],
    }


@router.get("")
def list_pipelines(db: Session = Depends(get_db)):
    runs = pipeline_repository.list_runs(db)
    return [_serialize_run(r) for r in runs]


@router.get("/{run_id}")
def get_pipeline(run_id: int, db: Session = Depends(get_db)):
    run = pipeline_repository.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return _serialize_run(run)


@router.post("", status_code=201)
def create_pipeline(
    payload: PipelineRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run = pipeline_repository.create_run(
        db,
        application_name=payload.application_name,
        git_repo=payload.git_repo,
        git_branch=payload.git_branch,
        environment=payload.environment,
    )
    background_tasks.add_task(pipeline_service.execute_pipeline, run.id)
    return _serialize_run(run)


@router.post("/trigger")
def trigger_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    application_name: str = Form(...),
    git_repo: str = Form(...),
    git_branch: str = Form("main"),
    environment: str = Form(...),
    db: Session = Depends(get_db),
):
    run = pipeline_repository.create_run(
        db,
        application_name=application_name,
        git_repo=git_repo,
        git_branch=git_branch,
        environment=environment,
    )
    background_tasks.add_task(pipeline_service.execute_pipeline, run.id)

    runs = pipeline_repository.list_runs(db)
    return templates.TemplateResponse(
        request,
        "_pipelines_fragment.html",
        {"pipelines": [_serialize_pipeline_for_web(r) for r in runs]},
    )


@router.post("/webhook/github", status_code=202)
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    try:
        payload = await request.json()
    except Exception:
        return {"message": "Payload JSON invalide"}

    if "ref" not in payload or "repository" not in payload:
        return {"message": "Ignoré : événement non pris en charge"}

    branch = payload["ref"].split("/")[-1]
    repo_url = payload["repository"]["clone_url"]

    apps = application_repository.get_all(db)
    
    # Nettoyage des URLs (espaces et suffixe .git) pour garantir la correspondance
    payload_repo_clean = repo_url.strip().lower().removesuffix(".git")

    matched_apps = [
        app for app in apps
        if (getattr(app, "git_repo") or "").strip().lower().removesuffix(".git") == payload_repo_clean 
        and (getattr(app, "git_branch") or "main") == branch
    ]

    if not matched_apps:
        return {"message": f"Ignoré : aucun job configuré pour {repo_url} sur la branche {branch}"}

    triggered_runs = []
    for app in matched_apps:
        run = pipeline_repository.create_run(
            db,
            application_name=app.name,
            git_repo=getattr(app, "git_repo") or "",
            git_branch=getattr(app, "git_branch") or "main",
            environment=getattr(app, "environment") or "Recette",
        )
        background_tasks.add_task(pipeline_service.execute_pipeline, run.id)
        triggered_runs.append(run.id)

    return {"message": "Pipelines déclenchés avec succès", "run_ids": triggered_runs}


@router.get("/{run_id}/status", response_class=HTMLResponse)
def get_pipeline_status(run_id: int, request: Request, db: Session = Depends(get_db)):
    """Route appelée par HTMX toutes les 2 secondes pour rafraîchir l'interface."""
    run = pipeline_repository.get_run(db, run_id)
    if not run:
        return HTMLResponse("Pipeline introuvable", status_code=404)
    
    pipeline_data = _serialize_pipeline_for_web(run)
    
    return templates.TemplateResponse(
        "fragments/pipeline_steps.html", 
        {"request": request, "pipeline": pipeline_data}
    )

@router.post("/webhook/github", status_code=202)
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Écoute les événements Push de GitHub.
    Si un push correspond à un Job configuré (même URL, même branche), 
    le pipeline est déclenché automatiquement.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"message": "Payload JSON invalide"}

    # 1. Vérifier si c'est bien un événement de "push" avec les données requises
    if "ref" not in payload or "repository" not in payload:
        return {"message": "Ignoré : événement non pris en charge"}

    # 2. Extraire la branche (ex: refs/heads/main -> main) et l'URL du dépôt
    branch = payload["ref"].split("/")[-1]
    repo_url = payload["repository"]["clone_url"] # ex: https://github.com/lunebadou/supply-chain-app.git

    # 3. Chercher dans la base s'il y a un Job configuré pour ce repo et cette branche
    apps = application_repository.get_all(db)
    matched_apps = [
        app for app in apps
        if app.repo_url.lower() == repo_url.lower() and app.branch == branch
    ]

    if not matched_apps:
        return {"message": f"Ignoré : aucun job configuré pour {repo_url} sur la branche {branch}"}

    # 4. Déclencher le pipeline pour le(s) job(s) correspondant(s)
    triggered_runs = []
    for app in matched_apps:
        # Créer l'historique du run en base
        run = repo.create_run(db, app.id)
        # Lancer le pipeline en tâche de fond (Git clone -> Ruff -> Bandit -> Deploy)
        background_tasks.add_task(pipeline_service.execute_pipeline, run.id)
        triggered_runs.append(run.id)

    return {"message": "Pipelines déclenchés avec succès", "run_ids": triggered_runs}