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