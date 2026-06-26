"""
Service d'orchestration du pipeline (CI/CD complet).
Exécute en arrière-plan : Clone Git → Ruff → Bandit → Déploiement Local (Docker Compose).
"""
import logging
import subprocess
import os
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PipelineStatus
from app.repositories import pipeline_repository
from app.clients import git_client
from app.services import analysis_service

logger = logging.getLogger("uniops.pipeline")

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
            code_path = git_client.clone_or_update(run.git_repo, run.git_branch)
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
            # On demande à Docker de monter l'image en arrière-plan (-d) et de forcer la reconstruction (--build)
            deploy_cmd = ["docker", "compose", "up", "-d", "--build"]
            
            # On force le nom du projet Docker avec le nom de l'application
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = run.application_name

            result = subprocess.run(
                deploy_cmd, 
                cwd=code_path, 
                env=env,
                capture_output=True, 
                text=True, 
                check=True
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