import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

@pytest.fixture(autouse=True)
def reset_db_state(monkeypatch, tmp_path):
    """Reset database module state between tests."""
    import backend.database as db_mod
    import backend.config as config_mod
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(config_mod, "DATABASE_PATH", test_db)
    monkeypatch.setattr(db_mod, "DATABASE_PATH", test_db)
    db_mod._connection = None
    db_mod._db_initialized = False
    yield
