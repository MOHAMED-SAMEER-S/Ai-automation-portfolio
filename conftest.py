import os
import sys
from pathlib import Path

# force safe offline settings BEFORE the app is imported (a real .env must never leak into tests)
for k, v in {"LLM_PROVIDER": "mock", "WA_MODE": "console", "CRM_MODE": "local", "EMAIL_MODE": "console",
             "META_APP_SECRET": "", "SECRET_KEY": "test-secret", "PUBLIC_BASE_URL": "http://test"}.items():
    os.environ[k] = v
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from core import config, db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.init()
    yield
