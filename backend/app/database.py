from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _resolve_database_url() -> str:
    url = settings.database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


_resolved_url = _resolve_database_url()

connect_args = (
    {"check_same_thread": False} if _resolved_url.startswith("sqlite") else {}
)

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if _resolved_url.startswith("postgresql"):
    engine_kwargs.update(
        {
            "pool_recycle": 300,
            "pool_use_lifo": True,
        }
    )

engine = create_engine(_resolved_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except DBAPIError:
            db.invalidate()
