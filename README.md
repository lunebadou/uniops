# UniOps

Plateforme AIOps unifiée pour environnements on-premise.
Projet de Fin d'Année (PFA) — Omnia School, 2025-2026.

## Stack

- Python 3.14 + FastAPI
- SQLite + SQLAlchemy
- Jinja2 + HTMX
- Prometheus + Grafana (monitoring)
- Jenkins (CI/CD)
- Docker (portabilité multi-OS)

## Lancement local

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
fastapi dev app/main.py
```