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

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Vérification

```bash
curl http://127.0.0.1:8000/health
```

Le endpoint doit répondre avec un JSON contenant `{"status":"ok","service":"uniops"}`.