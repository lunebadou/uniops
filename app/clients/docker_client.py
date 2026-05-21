"""
DockerClient — adaptateur unique vers le démon Docker.
Remplace à la fois ce que Jenkins ferait (build/run/restart)
et ce que Prometheus ferait (stats, logs).
"""
import docker
from docker.errors import DockerException


class DockerClient:
    def __init__(self):
        try:
            self._client = docker.from_env()
            self._client.ping()  # vérifie que le démon répond
        except DockerException as e:
            raise RuntimeError(f"Impossible de se connecter au démon Docker : {e}")

    def list_containers(self) -> list[dict]:
        """Liste les conteneurs en cours d'exécution avec leurs infos de base."""
        return [
            {
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "untagged",
                "status": c.status,
            }
            for c in self._client.containers.list()
        ]

    def get_container_stats(self, container_name: str) -> dict:
        """
        Récupère un snapshot des métriques d'un conteneur.
        Renvoie CPU (%), RAM (MB), RAM limit (MB).
        """
        try:
            container = self._client.containers.get(container_name)
        except docker.errors.NotFound:
            raise ValueError(f"Conteneur introuvable : {container_name}")

        stats = container.stats(stream=False)

        # CPU : formule officielle Docker
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

        # Mémoire
        mem_usage_mb = stats["memory_stats"].get("usage", 0) / (1024 * 1024)
        mem_limit_mb = stats["memory_stats"].get("limit", 1) / (1024 * 1024)

        return {
            "container_name": container_name,
            "status": container.status,
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(mem_usage_mb, 1),
            "memory_limit_mb": round(mem_limit_mb, 0),
        }


# Singleton instancié au démarrage de l'app
docker_client = DockerClient()