from sqlalchemy.orm import Session
from app.models import Application
from app.schemas.application import ApplicationCreate


def get_all(db: Session) -> list[Application]:
    return db.query(Application).all()


def get_by_id(db: Session, app_id: int) -> Application | None:
    return db.query(Application).filter(Application.id == app_id).first()


def create(db: Session, payload: ApplicationCreate) -> Application:
    app_obj = Application(**payload.model_dump())
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj


def delete(db: Session, app_id: int) -> bool:
    app_obj = get_by_id(db, app_id)
    if not app_obj:
        return False
    db.delete(app_obj)
    db.commit()
    return True