from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.models import Application, Environment, Metric, Anomaly, PipelineRun, PipelineStep  # noqa: F401
from app.routers import applications, monitoring, web, anomalies, pipelines
from app.core.scheduler import start_scheduler, stop_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="UniOps", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web.router)
app.include_router(applications.router)
app.include_router(monitoring.router)
app.include_router(anomalies.router)
app.include_router(pipelines.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "uniops"}