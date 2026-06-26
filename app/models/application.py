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


class PipelineStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    awaiting_validation = "awaiting_validation"
    rejected = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    git_repo = Column(String, nullable=True)
    git_branch = Column(String, nullable=False, default="main")
    environment = Column(String, nullable=False, default="Recette")
    created_at = Column(DateTime, default=datetime.utcnow)

    environments = relationship("Environment", back_populates="application", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="application", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    name = Column(String, nullable=False)
    target = Column(String, nullable=False)
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
    severity = Column(Enum(AnomalySeverity), nullable=False)
    observed_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    duration_points = Column(Integer, nullable=True)
    resolved = Column(Boolean, default=False)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    application_name = Column(String, nullable=False)
    git_repo = Column(String, nullable=False)
    git_branch = Column(String, nullable=False, default="main")
    environment = Column(String, nullable=False, default="Recette")
    status = Column(Enum(PipelineStatus), nullable=False, default=PipelineStatus.pending)
    human_validated = Column(Boolean, default=False)
    human_validated_by = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    application = relationship("Application", back_populates="pipeline_runs")
    steps = relationship("PipelineStep", back_populates="run", cascade="all, delete-orphan")


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    name = Column(String, nullable=False)
    order = Column(Integer, nullable=False, default=0)
    status = Column(Enum(PipelineStatus), nullable=False, default=PipelineStatus.pending)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    run = relationship("PipelineRun", back_populates="steps")