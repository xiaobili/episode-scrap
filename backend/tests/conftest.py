import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "episodescrap_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["ALLOWED_PATHS"] = "/tmp"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["TMDB_API_KEY"] = ""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import init_db
from app.main import app

init_db()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
