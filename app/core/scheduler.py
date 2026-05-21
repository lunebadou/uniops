"""
Scheduler in-process basé sur APScheduler.
Déclenche les tâches périodiques (collecte de métriques, détection
d'anomalies) sans nécessiter de conteneur cron séparé.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services import monitoring_service

logger = logging.getLogger("uniops.scheduler")
logger.setLevel(logging.INFO)

scheduler = BackgroundScheduler()


def collect_metrics_job():
    """Job de collecte exécuté à intervalle régulier."""
    db = SessionLocal()
    try:
        results = monitoring_service.collect_all_containers(db)
        logger.info(f"[scheduler] Collecte terminée : {len(results)} conteneurs")
    except Exception as e:
        logger.error(f"[scheduler] Erreur de collecte : {e}")
    finally:
        db.close()


def start_scheduler():
    """Démarre le scheduler avec les jobs récurrents."""
    if scheduler.running:
        return
    # Collecte toutes les 30 secondes
    scheduler.add_job(
        collect_metrics_job,
        trigger="interval",
        seconds=30,
        id="collect_metrics",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] Démarré — collecte des métriques toutes les 30s")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[scheduler] Arrêté")