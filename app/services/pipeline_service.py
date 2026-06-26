"""
Service d'orchestration du pipeline (CI/CD complet).
Exécute en arrière-plan : Clone Git → Ruff → Bandit → Déploiement Local (Docker Compose).
"""
import logging
import subprocess
import os
import re
import socket
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PipelineStatus
from app.repositories import pipeline_repository
from app.clients import git_client
from app.services import analysis_service

logger = logging.getLogger("uniops.pipeline")


def _find_free_ports(count: int) -> list[int]:
    sockets = []
    ports = []
    try:
        for _ in range(count):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", 0))
            ports.append(s.getsockname()[1])
            sockets.append(s)
    finally:
        for s in sockets:
            try:
                s.close()
            except Exception:
                pass
    return ports


def _extract_container_port(port_mapping: str) -> str | None:
    parts = [p.strip() for p in port_mapping.split(":") if p.strip()]
    if len(parts) >= 2:
        return parts[-1]
    return None


def _parse_compose_ports(code_path: Path) -> dict[str, list[str]]:
    compose_path = code_path / "docker-compose.yml"
    if not compose_path.exists():
        return {}

    services: dict[str, list[str]] = {}
    current_service = None
    in_ports = False

    for line in compose_path.read_text().splitlines():
        if line.startswith("services:"):
            current_service = None
            in_ports = False
            continue

        service_match = re.match(r"^\s{2}([^:\s][^:]*):\s*$", line)
        if service_match:
            current_service = service_match.group(1)
            in_ports = False
            continue

        if current_service is None:
            continue

        if re.match(r"^\s{4}ports:\s*$", line):
            in_ports = True
            continue

        if in_ports:
            port_match = re.match(r"^\s{6}-\s*\"?(.+?)\"?\s*$", line)
            if port_match:
                container_port = _extract_container_port(port_match.group(1))
                if container_port:
                    services.setdefault(current_service, []).append(container_port)
                continue
            if re.match(r"^\s{2}[^\s]", line):
                in_ports = False

    return services


def _build_compose_override(code_path: Path, safe_project_name: str) -> Path | None:
    service_ports = _parse_compose_ports(code_path)
    if not service_ports:
        return None

    port_count = sum(len(ports) for ports in service_ports.values())
    if port_count == 0:
        return None

    free_ports = _find_free_ports(port_count)
    override_path = code_path / "docker-compose.override.yml"

    with override_path.open("w", encoding="utf-8") as f:
        f.write("services:\n")
        index = 0
        for service, ports in service_ports.items():
            f.write(f"  {service}:\n")
            f.write("    ports:\n")
            for container_port in ports:
                host_port = free_ports[index]
                index += 1
                f.write(f"      - \"{host_port}:{container_port}\"\n")

    return override_path


def execute_pipeline(run_id: int) -> None:
    db: Session = SessionLocal()
    try:
        run = pipeline_repository.get_run(db, run_id)
        if not run:
            return

        logger.info(f"[pipeline] Démarrage run #{run_id} — {run.application_name} → {run.environment}")
        pipeline_repository.update_run_status(db, run_id, PipelineStatus.running)

        # ─── Étape 1 : Clone Git Local ───
        step1 = pipeline_repository.add_step(db, run_id, "Clone Git", order=1)
        pipeline_repository.start_step(db, step1.id)
        try:
            code_path = git_client.clone_or_update(run.git_repo, run.git_branch).resolve()
            pipeline_repository.finish_step(db, step1.id, success=True, output=f"Cloné localement : {code_path}")
        except Exception as e:
            pipeline_repository.finish_step(db, step1.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            return

        # ─── Étape 2 : Linter (Ruff) ───
        step2 = pipeline_repository.add_step(db, run_id, "Analyse Ruff", order=2)
        pipeline_repository.start_step(db, step2.id)
        try:
            ruff_report = analysis_service.run_ruff(code_path)
            pipeline_repository.finish_step(db, step2.id, success=True, output=analysis_service.format_ruff_summary(ruff_report))
        except Exception as e:
            pipeline_repository.finish_step(db, step2.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            return

        # ─── Étape 3 : Sécurité (Bandit) ───
        step3 = pipeline_repository.add_step(db, run_id, "Analyse Bandit", order=3)
        pipeline_repository.start_step(db, step3.id)
        try:
            bandit_report = analysis_service.run_bandit(code_path)
            pipeline_repository.finish_step(db, step3.id, success=True, output=analysis_service.format_bandit_summary(bandit_report))
        except Exception as e:
            pipeline_repository.finish_step(db, step3.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            return

        # ─── Étape 4 : Déploiement Local (Docker) ───
        step4 = pipeline_repository.add_step(db, run_id, f"Déploiement local ({run.environment})", order=4)
        pipeline_repository.start_step(db, step4.id)
        try:
            env = os.environ.copy()
            safe_project_name = re.sub(r"[^a-z0-9_-]", "-", run.application_name.lower().replace(" ", "-"))
            env["COMPOSE_PROJECT_NAME"] = safe_project_name

            override_file = _build_compose_override(code_path, safe_project_name)
            compose_files = ["docker-compose.yml"]
            if override_file:
                compose_files.append(str(override_file))

            down_cmd = ["docker", "compose"]
            for f in compose_files:
                down_cmd.extend(["-f", f])
            down_cmd.extend(["down", "--remove-orphans"])
            subprocess.run(
                down_cmd,
                cwd=code_path,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            deploy_cmd = ["docker", "compose"]
            for f in compose_files:
                deploy_cmd.extend(["-f", f])
            deploy_cmd.extend(["up", "-d", "--build"])
            result = subprocess.run(
                deploy_cmd,
                cwd=code_path,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            pipeline_repository.finish_step(db, step4.id, success=True, output=f"Déploiement local OK :\n{result.stdout}")
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.success)
        except subprocess.CalledProcessError as e:
            pipeline_repository.finish_step(db, step4.id, success=False, error_message=f"Erreur Docker:\n{e.stderr}")
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
        except Exception as e:
            pipeline_repository.finish_step(db, step4.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)

    finally:
        db.close()
