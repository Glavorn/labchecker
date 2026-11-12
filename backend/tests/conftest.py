import os
import tempfile

import pytest

_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["TEACHER_TOKEN"] = "test-token"
os.environ["MAX_UPLOAD_BYTES"] = "1024"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

TEACHER = {"X-Teacher-Token": "test-token"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def student(client):
    return client.post("/api/students", json={"full_name": "Иванов Иван"}, headers=TEACHER).json()


@pytest.fixture()
def py_lab(client):
    return client.post(
        "/api/labs", json={"title": "Lab 1", "language": "python"}, headers=TEACHER
    ).json()


@pytest.fixture()
def sh_lab(client):
    return client.post(
        "/api/labs", json={"title": "Lab 2", "language": "bash"}, headers=TEACHER
    ).json()
