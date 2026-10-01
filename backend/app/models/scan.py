"""SQLAlchemy models for WebGuard database."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.finding import FindingModel


class ScanModel(Base):
    """Lưu thông tin phiên quét và kết quả tổng quan."""

    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    mode: Mapped[str] = mapped_column(
        String(16), default="full", server_default="full", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Quan hệ 1 - Nhiều với bảng findings (khi xóa scan thì xóa luôn findings con)
    findings: Mapped[list["FindingModel"]] = relationship(
        "FindingModel",
        back_populates="scan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ScanModel(id={self.id}, target={self.target_url}, status={self.status})>"
