from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Float
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


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    git_repo = Column(String, nullable=True)  # ex: lunebadou/app-pfa
    created_at = Column(DateTime, default=datetime.utcnow)

    environments = relationship("Environment", back_populates="application", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(Enum(EnvironmentType), nullable=False)
    os_type = Column(Enum(OSType), nullable=False)
    host = Column(String, nullable=False)  # IP ou hostname
    port = Column(Integer, nullable=False, default=8000)
    prometheus_url = Column(String, nullable=True)  # endpoint /metrics
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