import os
import sqlite3
import tempfile
import pytest
from openmemo.migration import SchemaMigrator, CURRENT_SCHEMA_VERSION


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            content TEXT,
            created_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE cells (
            id INTEGER PRIMARY KEY,
            content TEXT,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


class TestSchemaMigrator:
    def test_initial_version(self, db_path):
        migrator = SchemaMigrator(db_path)
        version = migrator.get_schema_version()
        assert version == 1

    def test_run_migrations(self, db_path):
        migrator = SchemaMigrator(db_path)
        applied = migrator.run_migrations()
        assert 2 in applied
        assert migrator.get_schema_version() == CURRENT_SCHEMA_VERSION

    def test_idempotent(self, db_path):
        migrator = SchemaMigrator(db_path)
        migrator.run_migrations()
        applied_again = migrator.run_migrations()
        assert applied_again == []
        assert migrator.get_schema_version() == CURRENT_SCHEMA_VERSION

    def test_migration_adds_columns(self, db_path):
        migrator = SchemaMigrator(db_path)
        migrator.run_migrations()

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(notes)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        assert "memory_type" in columns
        assert "scene" in columns
        assert "fingerprint" in columns

    def test_rollback(self, db_path):
        migrator = SchemaMigrator(db_path)
        migrator.run_migrations()
        assert migrator.get_schema_version() == 2

        result = migrator.rollback(1)
        assert result == 1
        assert migrator.get_schema_version() == 1

    def test_rollback_invalid(self, db_path):
        migrator = SchemaMigrator(db_path)
        with pytest.raises(ValueError):
            migrator.rollback(0)

    def test_re_migrate_after_rollback(self, db_path):
        migrator = SchemaMigrator(db_path)
        migrator.run_migrations()
        migrator.rollback(1)
        applied = migrator.run_migrations()
        assert 2 in applied
        assert migrator.get_schema_version() == 2
