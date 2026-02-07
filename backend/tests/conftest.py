import pytest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

os.environ['SENTINEL_DB_PATH'] = ':memory:'

@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset database module state between tests."""
    import backend.database as db_mod
    db_mod._connection = None
    db_mod._db_initialized = False
    yield
