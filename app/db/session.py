
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для моделей базы данных."""


def get_db():
    """Создаёт сессию БД и закрывает её после использования."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
