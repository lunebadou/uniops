from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import Anomaly, AnomalyType, AnomalySeverity


def create(
    db: Session,
    container_name: str,
    anomaly_type: AnomalyType,
    severity: AnomalySeverity,
    observed_value: float | None = None,
    threshold_value: float | None = None,
    duration_points: int | None = None,
) -> Anomaly:
    anomaly = Anomaly(
        container_name=container_name,
        type=anomaly_type,
        severity=severity,
        observed_value=observed_value,
        threshold_value=threshold_value,
        duration_points=duration_points,
    )
    db.add(anomaly)
    db.commit()
    db.refresh(anomaly)
    return anomaly


def get_all(db: Session, only_unresolved: bool = False, limit: int = 200) -> list[Anomaly]:
    query = db.query(Anomaly)
    if only_unresolved:
        query = query.filter(Anomaly.resolved == False)
    return query.order_by(Anomaly.detected_at.desc()).limit(limit).all()


def get_by_id(db: Session, anomaly_id: int) -> Anomaly | None:
    return db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()


def count_unresolved(db: Session) -> int:
    return db.query(Anomaly).filter(Anomaly.resolved == False).count()


def has_recent_open_anomaly(
    db: Session,
    container_name: str,
    anomaly_type: AnomalyType,
    minutes: int = 5,
) -> bool:
    """Vérifie si une anomalie non résolue du même type existe déjà sur ce conteneur récemment.
    Évite de spammer la table à chaque cycle de collecte tant que le problème n'est pas résolu."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
    return db.query(Anomaly).filter(
        Anomaly.container_name == container_name,
        Anomaly.type == anomaly_type,
        Anomaly.resolved == False,
        Anomaly.detected_at >= since,
    ).first() is not None


def mark_resolved(db: Session, anomaly_id: int) -> bool:
    anomaly = get_by_id(db, anomaly_id)
    if not anomaly:
        return False
    anomaly.resolved = True
    anomaly.resolved_at = datetime.utcnow()
    db.commit()
    return True