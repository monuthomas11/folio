import os
import tempfile

import pytest

_test_db = os.path.join(tempfile.gettempdir(), "folio_test.db")
if os.path.exists(_test_db):
    os.remove(_test_db)

os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-1234567890"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Alert, Holding, User  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
    db = SessionLocal()
    try:
        db.query(Alert).delete()
        db.query(Holding).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}