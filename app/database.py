from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./uniops.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # spécifique SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI : ouvre une session DB par requête, la ferme après."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()