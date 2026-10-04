"""Integration test for Alembic database migrations."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def test_alembic_config(tmp_path: Path) -> Config:
    """Tạo config Alembic trỏ đến database tạm thời để kiểm thử upgrade và downgrade."""
    test_db_path = tmp_path / "test_migration.db"
    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_dir / "alembic.ini"

    config = Config(str(ini_path))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{test_db_path}")
    return config


def test_alembic_upgrade_and_downgrade(test_alembic_config: Config) -> None:
    """Kiểm tra quy trình chạy upgrade lên head và downgrade về base."""
    db_url = test_alembic_config.get_main_option("sqlalchemy.url")
    assert db_url is not None
    engine = create_engine(db_url)

    # 1. Chạy upgrade head -> Bảng scans và findings phải xuất hiện
    command.upgrade(test_alembic_config, "head")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "alembic_version" in tables
    assert "scans" in tables
    assert "findings" in tables

    # Kiểm tra các cột trong bảng scans
    scan_columns = [col["name"] for col in inspector.get_columns("scans")]
    assert "id" in scan_columns
    assert "target_url" in scan_columns
    assert "status" in scan_columns
    assert "score" in scan_columns
    assert "mode" in scan_columns

    # 2. Chạy downgrade base -> Các bảng phải được dọn dẹp sạch
    command.downgrade(test_alembic_config, "base")

    inspector = inspect(engine)
    tables_after = inspector.get_table_names()
    assert "scans" not in tables_after
    assert "findings" not in tables_after


def test_legacy_database_is_upgraded_with_mode_column(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DB cũ (tạo bằng create_all, chưa có cột mode) được init_db bổ sung cột và giữ dữ liệu."""
    from sqlalchemy import text

    import app.db.session as session_module

    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with legacy_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE scans (id VARCHAR(36) PRIMARY KEY, target_url VARCHAR(2048) NOT NULL,"
                " status VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL, completed_at DATETIME,"
                " score INTEGER, grade VARCHAR(10))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO scans (id, target_url, status, created_at)"
                " VALUES ('old-1', 'https://old.example.com', 'completed', '2026-09-01 00:00:00')"
            )
        )

    monkeypatch.setattr(session_module, "engine", legacy_engine)
    session_module.init_db()
    session_module.init_db()  # idempotent

    columns = [c["name"] for c in inspect(legacy_engine).get_columns("scans")]
    assert "mode" in columns
    with legacy_engine.connect() as conn:
        assert conn.execute(text("SELECT mode FROM scans WHERE id='old-1'")).scalar() == "full"
