"""Unit tests for ReportService."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.scan import scan_jobs
from app.core.errors import ScanNotFoundException
from app.db.session import Base
from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.schemas.scan import ScanStatus
from app.services.report import ReportService


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


@pytest.fixture
def report_service() -> ReportService:
    """Khởi tạo một instance ReportService mới cho test."""
    return ReportService()


def test_get_report_data_from_db(
    report_service: ReportService, db_session: Session
) -> None:
    """Kiểm tra tổng hợp dữ liệu báo cáo chuẩn xác từ bản ghi Database."""
    scan_id = str(uuid.uuid4())
    start_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    end_time = datetime(2026, 1, 1, 10, 0, 5, tzinfo=UTC)

    scan = ScanModel(
        id=scan_id,
        target_url="https://secure-target.com",
        status=ScanStatus.COMPLETED.value,
        created_at=start_time,
        completed_at=end_time,
        score=88,
        grade="B",
    )
    finding1 = FindingModel(
        scan_id=scan_id,
        module="headers",
        name="Missing CSP",
        severity="high",
        description="No Content-Security-Policy",
        remediation="Configure CSP",
        target_url="https://secure-target.com",
    )
    finding2 = FindingModel(
        scan_id=scan_id,
        module="cookies",
        name="Missing SameSite",
        severity="low",
        description="Cookie lacks SameSite attribute",
        remediation="Set SameSite=Lax",
        target_url="https://secure-target.com",
    )
    scan.findings.extend([finding1, finding2])
    db_session.add(scan)
    db_session.commit()

    report_data = report_service.get_report_data(scan_id=scan_id, db=db_session)

    assert report_data["scan_id"] == scan_id
    assert report_data["target_url"] == "https://secure-target.com"
    assert report_data["status"] == "completed"
    assert report_data["duration_seconds"] == 5.0
    assert report_data["total_findings"] == 2
    assert len(report_data["findings"]) == 2
    assert report_data["scoring"]["score"] == 88
    assert report_data["scoring"]["grade"] == "B"
    assert report_data["severity_counts"]["high"] == 1
    assert report_data["severity_counts"]["low"] == 1
    assert report_data["severity_counts"]["critical"] == 0
    assert report_data["severity_counts"]["medium"] == 0
    assert "generated_at" in report_data


def test_get_report_data_fallback_in_memory(
    report_service: ReportService,
) -> None:
    """Kiểm tra fallback đọc từ in-memory scan_jobs khi không có DB session."""
    scan_id = str(uuid.uuid4())
    scan_jobs[scan_id] = {
        "scan_id": scan_id,
        "target_url": "https://fallback.com",
        "status": ScanStatus.PENDING,
        "created_at": datetime.now(UTC),
        "findings": [],
        "scoring": {},
    }

    report_data = report_service.get_report_data(scan_id=scan_id, db=None)

    assert report_data["scan_id"] == scan_id
    assert report_data["target_url"] == "https://fallback.com"
    assert report_data["status"] == "pending"
    assert report_data["total_findings"] == 0
    assert report_data["findings"] == []
    assert report_data["scoring"] is None


def test_get_report_data_not_found(
    report_service: ReportService, db_session: Session
) -> None:
    """Kiểm tra ném ScanNotFoundException khi scan_id không tồn tại."""
    with pytest.raises(ScanNotFoundException):
        report_service.get_report_data(scan_id="unknown-uuid", db=db_session)


def test_generate_json_report(
    report_service: ReportService, db_session: Session
) -> None:
    """Kiểm tra tạo báo cáo JSON từ ReportService."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://example.com",
        status=ScanStatus.PENDING.value,
        created_at=datetime.now(UTC),
    )
    db_session.add(scan)
    db_session.commit()

    json_report = report_service.generate_json_report(scan_id=scan_id, db=db_session)
    assert isinstance(json_report, dict)
    assert json_report["scan_id"] == scan_id
    assert json_report["target_url"] == "https://example.com"


def test_generate_html_report_with_findings(
    report_service: ReportService, db_session: Session
) -> None:
    """Kiểm tra render HTML report qua Jinja2 template đầy đủ thông tin và findings."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://html-test.com",
        status=ScanStatus.COMPLETED.value,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        score=70,
        grade="C",
    )
    finding = FindingModel(
        scan_id=scan_id,
        module="ssl_tls",
        name="Expired SSL Certificate",
        severity="critical",
        description="The TLS certificate has expired",
        remediation="Renew certificate immediately",
        target_url="https://html-test.com",
    )
    scan.findings.append(finding)
    db_session.add(scan)
    db_session.commit()

    html = report_service.generate_html_report(scan_id=scan_id, db=db_session)

    assert "WebGuard" in html
    assert "https://html-test.com" in html
    assert scan_id in html
    assert "70 / 100" in html
    assert "grade-C" in html
    assert "Expired SSL Certificate" in html
    assert "Renew certificate immediately" in html
    assert "CRITICAL" in html or "critical" in html


def test_generate_html_report_no_findings(
    report_service: ReportService, db_session: Session
) -> None:
    """Kiểm tra render HTML khi phiên quét không phát hiện lỗ hổng nào."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://clean-site.com",
        status=ScanStatus.COMPLETED.value,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        score=100,
        grade="A+",
    )
    db_session.add(scan)
    db_session.commit()

    html = report_service.generate_html_report(scan_id=scan_id, db=db_session)

    assert "Không phát hiện vấn đề bảo mật nào" in html
    assert "100 / 100" in html


def test_get_export_filename(report_service: ReportService) -> None:
    """Kiểm tra định dạng tên file tải về chuẩn format."""
    long_uuid = "12345678-abcd-1234-ef00-1234567890ab"
    json_filename = report_service.get_export_filename(long_uuid, "json")
    html_filename = report_service.get_export_filename(long_uuid, "html")

    assert json_filename == "webguard_report_12345678.json"
    assert html_filename == "webguard_report_12345678.html"
