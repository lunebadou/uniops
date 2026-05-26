from sqlalchemy.orm import Session
from datetime import datetime

from app.models import PipelineRun, PipelineStep, PipelineStatus


# ───── PipelineRun ─────
def create_run(
    db: Session,
    application_name: str,
    git_repo: str,
    git_branch: str,
    environment: str,
) -> PipelineRun:
    run = PipelineRun(
        application_name=application_name,
        git_repo=git_repo,
        git_branch=git_branch,
        environment=environment,
        status=PipelineStatus.pending,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: int) -> PipelineRun | None:
    return db.query(PipelineRun).filter(PipelineRun.id == run_id).first()


def list_runs(db: Session, limit: int = 50) -> list[PipelineRun]:
    return (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )


def update_run_status(db: Session, run_id: int, status: PipelineStatus) -> bool:
    run = get_run(db, run_id)
    if not run:
        return False
    run.status = status
    if status in (PipelineStatus.success, PipelineStatus.failed, PipelineStatus.rejected):
        run.finished_at = datetime.utcnow()
    db.commit()
    return True


# ───── PipelineStep ─────
def add_step(db: Session, run_id: int, name: str, order: int) -> PipelineStep:
    step = PipelineStep(
        run_id=run_id,
        name=name,
        order=order,
        status=PipelineStatus.pending,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def start_step(db: Session, step_id: int) -> bool:
    step = db.query(PipelineStep).filter(PipelineStep.id == step_id).first()
    if not step:
        return False
    step.status = PipelineStatus.running
    step.started_at = datetime.utcnow()
    db.commit()
    return True


def finish_step(
    db: Session,
    step_id: int,
    success: bool,
    output: str | None = None,
    error_message: str | None = None,
) -> bool:
    step = db.query(PipelineStep).filter(PipelineStep.id == step_id).first()
    if not step:
        return False
    step.status = PipelineStatus.success if success else PipelineStatus.failed
    step.output = output
    step.error_message = error_message
    step.finished_at = datetime.utcnow()
    db.commit()
    return True