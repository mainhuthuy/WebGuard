from collections.abc import Generator
from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base, get_db
from app.models.finding import FindingModel
from app.models.scan import ScanModel


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Tạo database SQLite in-memory độc lập cho mỗi test case."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_create_scan_model(db_session: Session) -> None:
    """Kiểm tra tạo mới và truy vấn một bản ghi ScanModel."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://example.com",
        status="pending",
    )
    db_session.add(scan)
    db_session.commit()

    saved_scan = db_session.query(ScanModel).filter(ScanModel.id == scan_id).first()
    assert saved_scan is not None
    assert saved_scan.id == scan_id
    assert saved_scan.target_url == "https://example.com"
    assert saved_scan.status == "pending"
    assert saved_scan.score is None
    assert saved_scan.grade is None
    assert isinstance(saved_scan.created_at, datetime)
    assert "<ScanModel" in repr(saved_scan)


def test_scan_with_findings_relationship(db_session: Session) -> None:
    """Kiểm tra quan hệ 1-N giữa ScanModel và FindingModel."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://example.com",
        status="completed",
        score=85,
        grade="B",
        completed_at=datetime.now(timezone.utc),
    )

    finding1 = FindingModel(
        module="headers",
        name="Missing X-Frame-Options",
        severity="medium",
        description="Clickjacking vulnerability",
        remediation="Add X-Frame-Options header",
        target_url="https://example.com",
    )
    finding2 = FindingModel(
        module="cors",
        name="Wildcard Access-Control-Allow-Origin",
        severity="low",
        description="Origin is set to *",
        remediation="Restrict origins",
        target_url="https://example.com",
    )

    # Thêm findings vào quan hệ của scan
    scan.findings.extend([finding1, finding2])

    db_session.add(scan)
    db_session.commit()

    # Truy vấn lại
    queried_scan = db_session.query(ScanModel).filter(ScanModel.id == scan_id).first()
    assert queried_scan is not None
    assert len(queried_scan.findings) == 2
    assert queried_scan.findings[0].module == "headers"
    assert queried_scan.findings[0].scan_id == scan_id
    assert queried_scan.findings[0].scan.target_url == "https://example.com"
    assert "<FindingModel" in repr(queried_scan.findings[0])


def test_cascade_delete_findings_when_scan_deleted(db_session: Session) -> None:
    """Kiểm tra xóa Scan thì tất cả Finding con liên quan tự động bị xóa theo (cascade delete)."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://example.com",
        status="completed",
    )
    finding = FindingModel(
        module="ssl_tls",
        name="Weak TLS version",
        severity="high",
        description="TLS 1.0 supported",
        remediation="Upgrade to TLS 1.3",
    )
    scan.findings.append(finding)

    db_session.add(scan)
    db_session.commit()

    # Đảm bảo đã lưu thành công
    assert db_session.query(FindingModel).count() == 1

    # Xóa scan
    db_session.delete(scan)
    db_session.commit()

    # Finding cũng phải bị xóa sạch
    assert db_session.query(FindingModel).count() == 0


def test_get_db_yields_session() -> None:
    """Kiểm tra generator get_db() mở và đóng session chuẩn xác."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    with pytest.raises(StopIteration):
        next(db_gen)
