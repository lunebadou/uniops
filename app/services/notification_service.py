"""
Service de notifications — orchestre l'envoi d'emails pour les événements UniOps.
"""
from app import config
from app.clients.smtp_client import smtp_client
from app.models import Anomaly, AnomalyType, AnomalySeverity


_TYPE_LABEL = {
    AnomalyType.cpu_high: "CPU élevé",
    AnomalyType.memory_high: "Mémoire élevée",
    AnomalyType.container_stopped: "Conteneur arrêté",
}


def _build_anomaly_email(anomaly: Anomaly) -> tuple[str, str, str]:
    """Construit le sujet, le corps texte et le corps HTML d'un email d'anomalie."""
    type_label = _TYPE_LABEL.get(anomaly.type, anomaly.type.value)
    severity = anomaly.severity.value.upper()

    subject = f"[UniOps] {severity} — {type_label} sur {anomaly.container_name}"

    detected_at = anomaly.detected_at.strftime("%d/%m/%Y à %H:%M:%S")
    link = f"{config.UNIOPS_PUBLIC_URL}/anomalies"

    metric_line = ""
    if anomaly.observed_value is not None and anomaly.threshold_value is not None:
        metric_line = (
            f"Valeur observée : {anomaly.observed_value:.1f} "
            f"(seuil : {anomaly.threshold_value:.1f})\n"
        )

    body_text = (
        f"Une anomalie de sévérité {severity} a été détectée par UniOps.\n\n"
        f"Type        : {type_label}\n"
        f"Conteneur   : {anomaly.container_name}\n"
        f"Détectée le : {detected_at}\n"
        f"{metric_line}"
        f"\nConsulter le détail dans UniOps : {link}\n"
        f"\n— UniOps, plateforme AIOps unifiée"
    )

    body_html = f"""
    <html>
      <body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0d1117; color:#e6edf3; padding:20px;">
        <div style="max-width:600px; margin:auto; background:#161b22; border:1px solid #30363d; border-left:4px solid {'#f85149' if severity == 'CRITICAL' else '#f59e0b'}; border-radius:8px; padding:24px;">
          <div style="color:{'#f85149' if severity == 'CRITICAL' else '#f59e0b'}; font-weight:700; font-size:0.85rem; letter-spacing:1px; text-transform:uppercase;">{severity}</div>
          <h2 style="color:#f0f6fc; margin:8px 0 16px 0; font-size:1.3rem;">{type_label}</h2>
          <table style="width:100%; border-collapse:collapse; color:#e6edf3; font-size:0.9rem;">
            <tr>
              <td style="padding:6px 0; color:#8b949e; width:140px;">Conteneur</td>
              <td style="padding:6px 0; font-family:monospace; color:#58a6ff;">{anomaly.container_name}</td>
            </tr>
            <tr>
              <td style="padding:6px 0; color:#8b949e;">Détectée le</td>
              <td style="padding:6px 0;">{detected_at}</td>
            </tr>
            {"<tr><td style='padding:6px 0; color:#8b949e;'>Valeur observée</td><td style='padding:6px 0;'><strong>" + f"{anomaly.observed_value:.1f}" + "</strong> <span style='color:#8b949e;'>/ seuil " + f"{anomaly.threshold_value:.1f}" + "</span></td></tr>" if anomaly.observed_value is not None and anomaly.threshold_value is not None else ""}
          </table>
          <div style="margin-top:24px;">
            <a href="{link}" style="display:inline-block; background:#238636; color:white; padding:10px 18px; border-radius:6px; text-decoration:none; font-weight:600;">Voir dans UniOps</a>
          </div>
          <hr style="border:none; border-top:1px solid #30363d; margin:24px 0;">
          <div style="color:#8b949e; font-size:0.8rem;">UniOps — plateforme AIOps unifiée</div>
        </div>
      </body>
    </html>
    """

    return subject, body_text, body_html


def notify_anomaly(anomaly: Anomaly) -> bool:
    """Envoie une notification email pour une anomalie.
    Seules les anomalies de sévérité 'critical' déclenchent un envoi."""
    if anomaly.severity != AnomalySeverity.critical:
        return False

    subject, body_text, body_html = _build_anomaly_email(anomaly)
    return smtp_client.send(subject, body_text, body_html)