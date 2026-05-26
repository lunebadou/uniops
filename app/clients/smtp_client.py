"""
Client SMTP — encapsule l'envoi d'emails via smtplib (module standard Python).
Désactivable via SMTP_ENABLED=false dans .env.
"""
import smtplib
import logging
from email.message import EmailMessage

from app import config

logger = logging.getLogger("uniops.smtp")


class SMTPClient:
    def __init__(self):
        self.enabled = config.SMTP_ENABLED
        self.host = config.SMTP_HOST
        self.port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.sender = config.SMTP_FROM
        self.recipient = config.SMTP_TO

    def send(self, subject: str, body_text: str, body_html: str | None = None) -> bool:
        """Envoie un email. Retourne True si succès, False sinon (ou si désactivé)."""
        if not self.enabled:
            logger.info(f"[smtp] (désactivé) Email simulé : {subject}")
            return False

        if not self.host or not self.username:
            logger.warning("[smtp] Config SMTP incomplète, email non envoyé.")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info(f"[smtp] Email envoyé : {subject}")
            return True
        except Exception as e:
            logger.error(f"[smtp] Échec envoi email : {e}")
            return False


# Singleton
smtp_client = SMTPClient()