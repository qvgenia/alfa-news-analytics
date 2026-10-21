
import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url:
    engine = create_engine(database_url, pool_pre_ping=True)
else:
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set POSTGRES_PASSWORD or DATABASE_URL in .env"
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "alfa_app"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "alfa_hack"),
    )
    engine = create_engine(url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """Dependency для FastAPI: одна сессия на запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()