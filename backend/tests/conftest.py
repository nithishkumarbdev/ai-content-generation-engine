"""
Points the app at a temporary SQLite file instead of Postgres, so the test
suite doesn't depend on a running database server. Has to happen before
anything imports app.config, since settings are read from the environment
at import time - conftest.py is guaranteed to load first.
"""

import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="glitrai_test_")

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["STATIC_DIR"] = os.path.join(_TEST_DIR, "static")
os.environ["IMAGE_PROVIDER"] = "mock"

import pytest  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.utils.files import ensure_dirs  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _test_database():
    from app import models  # noqa: F401 - registers models on Base before create_all

    ensure_dirs()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
