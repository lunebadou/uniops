from sqlalchemy.orm import Session

from app.clients.docker_client import docker_client
from app.repositories import metric_repository
from app.services import anomaly_service, notification_service


def collect_all_containers(db: Session) -> list[dict]:
    """
    Cycle complet :
      1) scrape Docker
      2) persiste les métriques
      3) détecte les anomalies
      4) notifie par email les anomalies critiques
    """
    containers = docker_client.list_containers()
    results = []

    for container in containers:
        try:
            stats = docker_client.get_container_stats(container["name"])
            metric_repository.save(db, stats)
            results.append(stats)
        except Exception as e:
            results.append({"container_name": container["name"], "error": str(e)})

    # Détection d'anomalies
    anomalies = anomaly_service.check_all_containers(db)
    for a in anomalies:
        print(f"[ANOMALY] {a.container_name} — {a.type.value} (severity={a.severity.value})")
        # Notification email pour les anomalies critiques
        if notification_service.notify_anomaly(a):
            print(f"[EMAIL] Notification envoyée pour anomalie #{a.id}")

    return results