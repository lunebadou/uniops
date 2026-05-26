"""
Configuration centralisée d'UniOps, chargée depuis .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM (Phase D)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Seuils détection anomalies
ANOMALY_CPU_THRESHOLD = float(os.getenv("ANOMALY_CPU_THRESHOLD", "80.0"))
ANOMALY_MEMORY_THRESHOLD_MB = float(os.getenv("ANOMALY_MEMORY_THRESHOLD_MB", "2000"))
ANOMALY_DURATION_POINTS = int(os.getenv("ANOMALY_DURATION_POINTS", "3"))

# SMTP / Notifications
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "uniops@localhost")
SMTP_TO = os.getenv("SMTP_TO", "admin@localhost")
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"

# URL publique d'UniOps (pour les liens dans les emails)
UNIOPS_PUBLIC_URL = os.getenv("UNIOPS_PUBLIC_URL", "http://localhost:8888")