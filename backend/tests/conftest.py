"""Isolated database and offline providers: tests never use real credentials."""
import os
import tempfile

import pytest

_database_dir = tempfile.TemporaryDirectory(prefix="infogen-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + _database_dir.name.replace("\\", "/") + "/tests.db"
os.environ["AI_PROVIDER"] = "demo"
os.environ["DEMO_MODE"] = "true"


@pytest.fixture(scope="session", autouse=True)
def database():
    from app.models.database import init_db, engine
    init_db()
    yield
    engine.dispose()
    _database_dir.cleanup()
