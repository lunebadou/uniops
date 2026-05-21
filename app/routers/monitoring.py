from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clients.docker_client import docker_client
from app.database import get_db
from app.services import monitoring_service
from app.repositories import metric_repository

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/containers")
def list_containers():
    return docker_client.list_containers()


@router.get("/containers/{container_name}/stats")
def get_container_stats(container_name: str):
    try:
        return docker_client.get_container_stats(container_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/collect")
def trigger_collection(db: Session = Depends(get_db)):
    """Déclenche manuellement une collecte des métriques de tous les conteneurs."""
    results = monitoring_service.collect_all_containers(db)
    return {"collected": len(results), "results": results}


@router.get("/containers/{container_name}/history")
def get_history(container_name: str, minutes: int = 60, db: Session = Depends(get_db)):
    """Historique des métriques d'un conteneur sur les N dernières minutes."""
    history = metric_repository.get_history(db, container_name, minutes)
    return [
        {
            "collected_at": m.collected_at.isoformat(),
            "cpu_percent": m.cpu_percent,
            "memory_mb": m.memory_mb,
            "status": m.status,
        }
        for m in history
    ]