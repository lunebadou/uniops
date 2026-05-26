from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class EnvironmentType(str, enum.Enum):
    test = "test"
    recette = "recette"
    production = "production"


class OSType(str, enum.Enum):
    ubuntu = "ubuntu"
    windows = "windows"


class AnomalyType(str, enum.Enum):
    cpu_high = "cpu_high"
    memory_high = "memory_high"
    container_stopped = "container_stopped"


class AnomalySeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    git_repo = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    environments = relationship("Environment", back_populates="application", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(EnvironmentType), nullable=False)
    os_type = Column(Enum(OSType), nullable=False)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False, default=8000)
    prometheus_url = Column(String, nullable=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="environments")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    container_name = Column(String, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_mb = Column(Float, nullable=False)
    memory_limit_mb = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    collected_at = Column(DateTime, default=datetime.utcnow, index=True)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    container_name = Column(String, nullable=False, index=True)
    type = Column(Enum(AnomalyType), nullable=False)
    severity = Column(Enum(AnomalySeverity), nullable=False, default=AnomalySeverity.warning)

    # Contexte de l'anomalie
    observed_value = Column(Float, nullable=True)       # ex: 92.5 (% CPU)
    threshold_value = Column(Float, nullable=True)      # ex: 80.0
    duration_points = Column(Integer, nullable=True)    # nb de mesures consécutives au-dessus

    # Analyse IA (sera rempli en étape 3)
    ai_analysis = Column(Text, nullable=True)
    ai_analyzed_at = Column(DateTime, nullable=True)

    # Cycle de vie
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

class PipelineStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    awaiting_validation = "awaiting_validation"
    rejected = "rejected"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)

    # Cible du déploiement
    application_name = Column(String, nullable=False, index=True)   # ex: "supply-chain-app"
    git_repo = Column(String, nullable=False)                       # ex: "lunebadou/supply-chain-app"
    git_branch = Column(String, nullable=False, default="main")
    environment = Column(String, nullable=False)                    # "recette" ou "production"

    # État global
    status = Column(Enum(PipelineStatus), nullable=False, default=PipelineStatus.pending)

    # Analyse IA (rempli plus tard en étape 4)
    ai_risk_level = Column(String, nullable=True)                   # "low", "medium", "high"
    ai_summary = Column(Text, nullable=True)                        # résumé IA du diff
    ai_validated = Column(Boolean, default=False)                   # IA a-t-elle approuvé ?

    # Validation humaine (rempli plus tard si environnement = production)
    human_validated = Column(Boolean, default=False)
    human_validated_by = Column(String, nullable=True)              # "admin" pour l'instant

    # Cycle de vie
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)

    # Relation avec les étapes
    steps = relationship("PipelineStep", back_populates="run", cascade="all, delete-orphan", order_by="PipelineStep.order")


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)

    name = Column(String, nullable=False)              # ex: "Clone Git", "Analyse Ruff", "Build Docker"
    order = Column(Integer, nullable=False)            # position dans le pipeline (1, 2, 3...)
    status = Column(Enum(PipelineStatus), nullable=False, default=PipelineStatus.pending)

    # Sortie de l'étape (stdout/stderr, rapports JSON, etc.)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    run = relationship("PipelineRun", back_populates="steps")