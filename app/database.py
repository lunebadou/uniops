from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./uniops.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # spécifique SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _ensure_schema() -> None:
    """Ajoute automatiquement les colonnes manquantes sur la base SQLite locale."""
    with engine.begin() as conn:
        inspector = inspect(conn)

        if inspector.has_table("applications"):
            columns = {col["name"] for col in inspector.get_columns("applications")}
            if "description" not in columns:
                conn.execute(text("ALTER TABLE applications ADD COLUMN description VARCHAR"))
            if "git_repo" not in columns:
                conn.execute(text("ALTER TABLE applications ADD COLUMN git_repo VARCHAR"))
            if "git_branch" not in columns:
                conn.execute(text("ALTER TABLE applications ADD COLUMN git_branch VARCHAR NOT NULL DEFAULT 'main'"))
            if "environment" not in columns:
                conn.execute(text("ALTER TABLE applications ADD COLUMN environment VARCHAR NOT NULL DEFAULT 'Recette'"))
            if "created_at" not in columns:
                conn.execute(text("ALTER TABLE applications ADD COLUMN created_at DATETIME"))

        if inspector.has_table("pipeline_runs"):
            columns = {col["name"] for col in inspector.get_columns("pipeline_runs")}
            if "application_id" not in columns:
                conn.execute(text("ALTER TABLE pipeline_runs ADD COLUMN application_id INTEGER"))


_ensure_schema()
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency FastAPI : ouvre une session DB par requête, la ferme après."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()