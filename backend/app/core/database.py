from __future__ import annotations

import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def wait_for_database(max_retries: int = 30, sleep_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for _ in range(max_retries):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover
            last_error = exc
            time.sleep(sleep_seconds)
    if last_error is not None:
        raise last_error


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()