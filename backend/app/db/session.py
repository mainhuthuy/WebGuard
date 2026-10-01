"""Database session and engine configuration using SQLAlchemy."""

from collections.abc import Generator
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core import get_settings

logger = logging.getLogger("app.db.session")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


# Lấy URL từ settings
settings = get_settings()

# Với SQLite, cần check_same_thread=False để hỗ trợ đa luồng trong FastAPI
connect_args = {}
if settings.DB_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DB_URL,
    connect_args=connect_args,
    echo=settings.DEBUG and settings.ENV == "development",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency để tạo và tự động đóng database session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _upgrade_legacy_schema() -> None:
    """Bổ sung các cột mới cho database cũ được tạo bằng create_all (không qua Alembic).

    create_all không sửa bảng đã tồn tại, nên các cột thêm sau này phải được thêm thủ công.
    Môi trường dùng Alembic (`alembic upgrade head`) đã có sẵn các cột này.
    """
    inspector = inspect(engine)
    if "scans" not in inspector.get_table_names():
        return
    scan_columns = {col["name"] for col in inspector.get_columns("scans")}
    if "mode" not in scan_columns:
        logger.info("Nâng cấp schema: thêm cột scans.mode")
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE scans ADD COLUMN mode VARCHAR(16) NOT NULL DEFAULT 'full'")
            )


def init_db() -> None:
    """Khởi tạo toàn bộ database tables nếu chưa tồn tại và nâng cấp schema cũ."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _upgrade_legacy_schema()

