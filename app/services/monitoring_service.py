from sqlalchemy.orm import Session

from app.clients.docker_client import docker_client
from app.repositories import metric_repository


def collect_all_containers(db: Session) -> list[dict]:
    """
    Cycle de collecte : scanne tous les conteneurs Docker actifs,
    persiste leurs métriques en base, renvoie le résultat.
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

    return results