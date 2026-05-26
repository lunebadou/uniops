"""
Service de détection d'anomalies.
Analyse l'historique récent des métriques et crée des anomalies
lorsque les seuils sont dépassés sur N mesures consécutives.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import (
    ANOMALY_CPU_THRESHOLD,
    ANOMALY_MEMORY_THRESHOLD_MB,
    ANOMALY_DURATION_POINTS,
)
from app.models import Metric, Anomaly, AnomalyType, AnomalySeverity
from app.repositories import anomaly_repository


def _severity_for_cpu(value: float) -> AnomalySeverity:
    if value >= 95:
        return AnomalySeverity.critical
    if value >= 80:
        return AnomalySeverity.warning
    return AnomalySeverity.info


def _severity_for_memory(value: float, limit: float) -> AnomalySeverity:
    if limit <= 0:
        return AnomalySeverity.warning
    ratio = value / limit
    if ratio >= 0.95:
        return AnomalySeverity.critical
    if ratio >= 0.8:
        return AnomalySeverity.warning
    return AnomalySeverity.info


def check_container(db: Session, container_name: str) -> list[Anomaly]:
    """Évalue les seuils sur les N dernières mesures du conteneur.
    Renvoie la liste des anomalies créées lors de ce check."""
    created: list[Anomaly] = []

    recent = (
        db.query(Metric)
        .filter(Metric.container_name == container_name)
        .order_by(desc(Metric.collected_at))
        .limit(ANOMALY_DURATION_POINTS)
        .all()
    )

    if len(recent) < ANOMALY_DURATION_POINTS:
        return created  # pas assez de données pour décider

    # CPU élevé sur N mesures consécutives
    if all(m.cpu_percent >= ANOMALY_CPU_THRESHOLD for m in recent):
        if not anomaly_repository.has_recent_open_anomaly(db, container_name, AnomalyType.cpu_high):
            latest = recent[0]
            anomaly = anomaly_repository.create(
                db,
                container_name=container_name,
                anomaly_type=AnomalyType.cpu_high,
                severity=_severity_for_cpu(latest.cpu_percent),
                observed_value=latest.cpu_percent,
                threshold_value=ANOMALY_CPU_THRESHOLD,
                duration_points=ANOMALY_DURATION_POINTS,
            )
            created.append(anomaly)

    # Mémoire élevée
    if all(m.memory_mb >= ANOMALY_MEMORY_THRESHOLD_MB for m in recent):
        if not anomaly_repository.has_recent_open_anomaly(db, container_name, AnomalyType.memory_high):
            latest = recent[0]
            anomaly = anomaly_repository.create(
                db,
                container_name=container_name,
                anomaly_type=AnomalyType.memory_high,
                severity=_severity_for_memory(latest.memory_mb, latest.memory_limit_mb),
                observed_value=latest.memory_mb,
                threshold_value=ANOMALY_MEMORY_THRESHOLD_MB,
                duration_points=ANOMALY_DURATION_POINTS,
            )
            created.append(anomaly)

    # Conteneur arrêté (statut != running sur le dernier point)
    latest = recent[0]
    if latest.status != "running":
        if not anomaly_repository.has_recent_open_anomaly(db, container_name, AnomalyType.container_stopped):
            anomaly = anomaly_repository.create(
                db,
                container_name=container_name,
                anomaly_type=AnomalyType.container_stopped,
                severity=AnomalySeverity.critical,
            )
            created.append(anomaly)

    return created


def check_all_containers(db: Session) -> list[Anomaly]:
    """Évalue tous les conteneurs ayant des métriques récentes en base."""
    distinct = db.query(Metric.container_name).distinct().all()
    container_names = [row[0] for row in distinct]

    all_created: list[Anomaly] = []
    for name in container_names:
        all_created.extend(check_container(db, name))
    return all_created