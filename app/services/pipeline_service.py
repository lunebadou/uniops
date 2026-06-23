"""
Service d'orchestration du pipeline.
Exécute en arrière-plan : Clone Git → Analyse Ruff → Analyse Bandit → Routage RCT/PROD.
(Le build Docker viendra s'insérer ici plus tard)
"""
import logging
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PipelineStatus
from app.repositories import pipeline_repository
from app.clients import git_client
from app.services import analysis_service

logger = logging.getLogger("uniops.pipeline")


def execute_pipeline(run_id: int) -> None:
    """
    Point d'entrée appelé en arrière-plan (BackgroundTasks).
    Ouvre sa propre session DB car on est hors du cycle de requête HTTP.
    """
    db: Session = SessionLocal()
    try:
        run = pipeline_repository.get_run(db, run_id)
        if not run:
            logger.error(f"[pipeline] Run #{run_id} introuvable")
            return

        logger.info(f"[pipeline] Démarrage run #{run_id} — {run.application_name} → {run.environment}")
        pipeline_repository.update_run_status(db, run_id, PipelineStatus.running)

        # ─── Étape 1 : Clone Git ───
        step1 = pipeline_repository.add_step(db, run_id, "Clone Git", order=1)
        pipeline_repository.start_step(db, step1.id)
        try:
            code_path = git_client.clone_or_update(run.git_repo, run.git_branch)
            pipeline_repository.finish_step(
                db, step1.id,
                success=True,
                output=f"Repository cloné dans {code_path}",
            )
            logger.info(f"[pipeline] Clone OK : {code_path}")
        except Exception as e:
            pipeline_repository.finish_step(
                db, step1.id,
                success=False,
                error_message=f"Échec du clone : {e}",
            )
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            logger.error(f"[pipeline] Clone échoué : {e}")
            return

        # ─── Étape 2 : Analyse Ruff (Linter) ───
        step2 = pipeline_repository.add_step(db, run_id, "Analyse Ruff (linter)", order=2)
        pipeline_repository.start_step(db, step2.id)
        ruff_report = None
        try:
            ruff_report = analysis_service.run_ruff(code_path)
            summary = analysis_service.format_ruff_summary(ruff_report)
            pipeline_repository.finish_step(
                db, step2.id,
                success=True,
                output=summary,
            )
            logger.info(f"[pipeline] Ruff terminé : {ruff_report['issues_count']} issues")
        except Exception as e:
            pipeline_repository.finish_step(db, step2.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            return

        # ─── Étape 3 : Analyse Bandit (Sécurité) ───
        step3 = pipeline_repository.add_step(db, run_id, "Analyse Bandit (sécurité)", order=3)
        pipeline_repository.start_step(db, step3.id)
        bandit_report = None
        try:
            bandit_report = analysis_service.run_bandit(code_path)
            summary = analysis_service.format_bandit_summary(bandit_report)
            pipeline_repository.finish_step(
                db, step3.id,
                success=True,
                output=summary,
            )
            logger.info(f"[pipeline] Bandit terminé : {bandit_report['issues_count']} issues")
        except Exception as e:
            pipeline_repository.finish_step(db, step3.id, success=False, error_message=str(e))
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
            return

        # ─── Étape 4 : Routage RCT vs PROD (Logique Souveraine) ───
        env_cible = run.environment.lower()
        
        if env_cible in ["recette", "rct", "test", "dev"]:
            logger.info(f"[pipeline] Environnement {env_cible} détecté : Auto-approbation (Continuous Deployment)")
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.success)
            # TODO : Intégrer docker-py ici pour le déploiement
            
        elif env_cible in ["production", "prod"]:
            logger.info(f"[pipeline] Environnement {env_cible} détecté : Mise en attente de validation humaine (Continuous Delivery)")
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.awaiting_validation)
            
        else:
            logger.warning(f"[pipeline] Environnement inconnu ({env_cible}), mise en attente par précaution.")
            pipeline_repository.update_run_status(db, run_id, PipelineStatus.awaiting_validation)

    except Exception as e:
        logger.error(f"[pipeline] Erreur critique lors de l'exécution : {e}")
        pipeline_repository.update_run_status(db, run_id, PipelineStatus.failed)
    finally:
        db.close()