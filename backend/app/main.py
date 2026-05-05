from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import Base, engine, wait_for_database
from app.core.migrations import ensure_database_schema
from app.models import entities  # noqa: F401


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)
    ensure_database_schema(engine)


app.include_router(router)
