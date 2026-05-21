from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import Metric


def save(db: Session, data: dict) -> Metric:
    """Persiste un snapshot de métriques."""
    metric = Metric(
        container_name=data["container_name"],
        cpu_percent=data["cpu_percent"],
        memory_mb=data["memory_mb"],
        memory_limit_mb=data["memory_limit_mb"],
        status=data["status"],
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def get_history(db: Session, container_name: str, minutes: int = 60) -> list[Metric]:
    """Récupère l'historique des métriques d'un conteneur sur les N dernières minutes."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return (
        db.query(Metric)
        .filter(Metric.container_name == container_name)
        .filter(Metric.collected_at >= since)
        .order_by(Metric.collected_at.asc())
        .all()
    )


def get_latest(db: Session, container_name: str) -> Metric | None:
    """Récupère le dernier snapshot d'un conteneur."""
    return (
        db.query(Metric)
        .filter(Metric.container_name == container_name)
        .order_by(Metric.collected_at.desc())
        .first()
    )