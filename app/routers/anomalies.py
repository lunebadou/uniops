from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.database import get_db
from app.repositories import anomaly_repository
from app.clients.smtp_client import smtp_client

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


def _serialize(items) -> list[dict]:
    return [
        {
            "id": a.id,
            "container_name": a.container_name,
            "type": a.type.value,
            "severity": a.severity.value,
            "observed_value": a.observed_value,
            "threshold_value": a.threshold_value,
            "duration_points": a.duration_points,
            "ai_analysis": a.ai_analysis,
            "detected_at": a.detected_at.isoformat(),
            "detected_at_fmt": a.detected_at.strftime("%d/%m/%Y %H:%M:%S"),
            "resolved": a.resolved,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "resolved_at_fmt": a.resolved_at.strftime("%d/%m/%Y %H:%M:%S") if a.resolved_at else None,
        }
        for a in items
    ]


@router.get("")
def list_anomalies(only_unresolved: bool = False, db: Session = Depends(get_db)):
    items = anomaly_repository.get_all(db, only_unresolved=only_unresolved)
    return _serialize(items)


@router.get("/count")
def count_open(db: Session = Depends(get_db)):
    return {"open": anomaly_repository.count_unresolved(db)}


@router.post("/{anomaly_id}/resolve")
def resolve(anomaly_id: int, request: Request, db: Session = Depends(get_db)):
    if not anomaly_repository.mark_resolved(db, anomaly_id):
        raise HTTPException(status_code=404, detail="Anomaly not found")

    if request.headers.get("hx-request"):
        items = anomaly_repository.get_all(db, only_unresolved=False)
        return templates.TemplateResponse(
            request,
            "_anomalies_fragment.html",
            {"anomalies": _serialize(items)},
        )

    return {"id": anomaly_id, "resolved": True}


@router.post("/test-email")
def test_email():
    """Endpoint utilitaire : envoie un email de test via la config SMTP active.
    Permet de valider la connexion Mailtrap avant qu'une vraie anomalie ne survienne."""
    ok = smtp_client.send(
        subject="[UniOps] Test SMTP",
        body_text="Si vous recevez cet email, la configuration SMTP UniOps est opérationnelle.",
        body_html="<p>Si vous recevez cet email, la configuration SMTP UniOps est <strong>opérationnelle</strong>.</p>",
    )
    return {"sent": ok}