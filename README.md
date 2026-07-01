# UniOps

Plateforme AIOps unifiée pour environnements on-premise.
Projet de Fin d'Année (PFA) – Omnia School, 2025-2026.

## Stack

- Python 3.11 + FastAPI
- SQLite + SQLAlchemy (Persistance de l'état des pipelines et des anomalies)
- Jinja2 + HTMX (Interface et monitoring natif en temps réel)
- Docker & Docker Compose (Orchestration et portabilité multi-OS)
- Ngrok (Tunnel sécurisé pour l'exposition des Webhooks GitHub)
- Google GenAI / Gemini (AIOps pour le diagnostic des logs)

## Lancement local

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Windows PowerShell
PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Vérification
Bash
curl [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
Le endpoint doit répondre avec un JSON contenant {"status":"ok","service":"uniops"}.