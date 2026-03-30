
import pytest

from velocity.infra.db.sqlite_backend import SQLiteBackend


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")

@pytest.mark.asyncio
async def test_sqlite_backend_lifecycle(db_path):
    backend = SQLiteBackend(db_path)
    # Ensure initialized
    assert await backend.health_check() is True
    
    # 1. Create table
    await backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    
    # 2. Insert with parameters
    # Note: aiosqlite uses ? for positional or :name for named
    await backend.execute("INSERT INTO test (name) VALUES (:name)", {"name": "alice"})
    
    # 3. Fetch one
    row = await backend.fetch_one("SELECT * FROM test WHERE name = :name", {"name": "alice"})
    assert row["name"] == "alice"
    
    # 4. Fetch all
    rows = await backend.fetch_all("SELECT * FROM test")
    assert len(rows) == 1
    assert rows[0]["name"] == "alice"

@pytest.mark.asyncio
async def test_sqlite_backend_health_check_fail(tmp_path):
    # Point to a directory instead of a file to force error
    invalid_path = str(tmp_path) 
    backend = SQLiteBackend(invalid_path)
    # This might still return True if it's a valid path for sqlite to create, 
    # so we use a definitely invalid one or close it.
    # Actually, if we use a path that is a directory, it should fail.
    assert await backend.health_check() is False
