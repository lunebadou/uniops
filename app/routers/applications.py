from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.repositories import application_repository as repo

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", response_model=list[ApplicationRead])
def list_applications(db: Session = Depends(get_db)):
    return repo.get_all(db)


@router.get("/{app_id}", response_model=ApplicationRead)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app_obj = repo.get_by_id(db, app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    return app_obj


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    return repo.create(db, payload)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    if not repo.delete(db, app_id):
        raise HTTPException(status_code=404, detail="Application not found")