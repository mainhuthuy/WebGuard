"""Unit tests for ScanService lifecycle management."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import ScanNotFoundException
from app.db.session import Base
from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.modules.scanner import Scanner
from app.schemas.scan import (
    Finding,
    ScanEventType,
    ScanResponse,
    ScanStatus,
    ScoringResult,
    SeverityLevel,
)
from app.services.scan import ScanService


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
def scan_service() -> ScanService:
    """Khởi tạo một instance ScanService mới cho test."""
    return ScanService()


def test_create_scan(scan_service: ScanService, db_session: Session) -> None:
    """Kiểm tra khởi tạo một phiên quét mới với trạng thái pending."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    assert scan is not None
    assert scan.id is not None
    assert scan.target_url == "https://example.com"
    assert scan.status == ScanStatus.PENDING.value
    assert isinstance(scan.created_at, datetime)
    assert scan.completed_at is None
    assert scan.score is None
    assert scan.grade is None


def test_get_scan_and_get_scan_or_404(
    scan_service: ScanService, db_session: Session
) -> None:
    """Kiểm tra truy vấn phiên quét từ DB và ném 404 khi không tồn tại."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    retrieved = scan_service.get_scan(db=db_session, scan_id=scan.id)
    assert retrieved is not None
    assert retrieved.id == scan.id

    # Test không tìm thấy
    assert (
        scan_service.get_scan(db=db_session, scan_id="non-existent-uuid") is None
    )

    with pytest.raises(ScanNotFoundException):
        scan_service.get_scan_or_404(db=db_session, scan_id="non-existent-uuid")


@pytest.mark.asyncio
async def test_execute_scan_success(
    scan_service: ScanService, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra thực thi scan thành công: chuyển running -> completed, lưu findings & điểm."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    # Mock Scanner.scan
    mock_findings = [
        Finding(
            module="headers",
            name="Missing CSP",
            severity=SeverityLevel.HIGH,
            description="No CSP header",
            remediation="Add CSP",
            url="https://example.com",
        ),
        Finding(
            module="cookies",
            name="Missing HttpOnly",
            severity=SeverityLevel.MEDIUM,
            description="Cookie lacks HttpOnly",
            remediation="Add HttpOnly",
            url="https://example.com",
        ),
    ]
    mock_scan_res = ScanResponse(
        scan_id=scan.id,
        url="https://example.com",
        status=ScanStatus.COMPLETED,
        total_findings=2,
        findings=mock_findings,
        scoring=ScoringResult(score=75, grade="C", total_findings=2),
    )

    async def mock_scan(self: Any, url: str) -> ScanResponse:
        return mock_scan_res

    monkeypatch.setattr(Scanner, "scan", mock_scan)

    completed_scan = await scan_service.execute_scan(
        scan_id=scan.id, db=db_session
    )

    assert completed_scan.status == ScanStatus.COMPLETED.value
    assert completed_scan.score == 75
    assert completed_scan.grade == "C"
    assert completed_scan.completed_at is not None

    # Kiểm tra findings đã được lưu vào database
    saved_findings = (
        db_session.query(FindingModel)
        .filter(FindingModel.scan_id == scan.id)
        .all()
    )
    assert len(saved_findings) == 2
    assert saved_findings[0].module == "headers"
    assert saved_findings[0].name == "Missing CSP"
    assert saved_findings[0].severity == "high"


@pytest.mark.asyncio
async def test_execute_scan_failure(
    scan_service: ScanService, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra khi scan bị crash thì cập nhật trạng thái failed."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    async def mock_scan_error(self: Any, url: str) -> ScanResponse:
        raise RuntimeError("Network failure during scan")

    monkeypatch.setattr(Scanner, "scan", mock_scan_error)

    with pytest.raises(RuntimeError):
        await scan_service.execute_scan(scan_id=scan.id, db=db_session)

    db_session.refresh(scan)
    assert scan.status == ScanStatus.FAILED.value
    assert scan.completed_at is not None


@pytest.mark.asyncio
async def test_cancel_scan_pending_and_running(
    scan_service: ScanService, db_session: Session
) -> None:
    """Kiểm tra hủy phiên quét khi đang pending hoặc running."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    # Giả lập gắn một asyncio task đang chạy
    async def dummy_coro() -> None:
        await asyncio.sleep(10)

    task = asyncio.create_task(dummy_coro())
    scan_service._active_tasks[scan.id] = task

    success = scan_service.cancel_scan(db=db_session, scan_id=scan.id)
    assert success is True
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert task.cancelled()


    db_session.refresh(scan)
    assert scan.status == ScanStatus.CANCELLED.value
    assert scan.completed_at is not None

    # Thử hủy lại khi đã CANCELLED -> Trả về False
    assert scan_service.cancel_scan(db=db_session, scan_id=scan.id) is False


def test_cancel_scan_terminal_states(
    scan_service: ScanService, db_session: Session
) -> None:
    """Kiểm tra không thể hủy scan đã hoàn tất hoặc thất bại."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")
    scan.status = ScanStatus.COMPLETED.value
    db_session.commit()

    assert scan_service.cancel_scan(db=db_session, scan_id=scan.id) is False

    scan.status = ScanStatus.FAILED.value
    db_session.commit()

    assert scan_service.cancel_scan(db=db_session, scan_id=scan.id) is False

    # Scan ID không tồn tại
    assert (
        scan_service.cancel_scan(db=db_session, scan_id="unknown-uuid") is False
    )


@pytest.mark.asyncio
async def test_start_background_scan(
    scan_service: ScanService, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra khởi chạy background task và dọn dẹp task khi hoàn thành."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    async def mock_execute(scan_id: str, db: Session | None = None) -> ScanModel:
        await asyncio.sleep(0.01)
        scan.status = ScanStatus.COMPLETED.value
        return scan

    monkeypatch.setattr(scan_service, "execute_scan", mock_execute)

    task = scan_service.start_background_scan(scan_id=scan.id)
    assert scan.id in scan_service._active_tasks

    await task
    # Sau khi task hoàn tất, done callback đã dọn dẹp khỏi _active_tasks
    assert scan.id not in scan_service._active_tasks


@pytest.mark.asyncio
async def test_stream_scan_persists_to_db_and_replay(
    scan_service: ScanService, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra stream_scan phát sự kiện, lưu DB và có thể replay lại khi hoàn tất."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    async def mock_scan_stream(
        self: Any, url: str, scan_id: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {
            "event": ScanEventType.START.value,
            "scan_id": scan_id,
            "progress": 0,
            "message": "Start scan",
            "module": None,
            "findings": None,
            "data": None,
        }
        yield {
            "event": ScanEventType.COMPLETE.value,
            "scan_id": scan_id,
            "progress": 100,
            "message": "Scan completed",
            "module": None,
            "findings": [
                {
                    "module": "headers",
                    "name": "Missing CSP",
                    "severity": "high",
                    "description": "desc",
                    "remediation": "rem",
                    "url": url,
                }
            ],
            "data": {
                "scoring": {"score": 85, "grade": "B", "total_findings": 1}
            },
        }

    monkeypatch.setattr(Scanner, "scan_stream", mock_scan_stream)

    # 1. Chạy stream lần đầu
    events = []
    async for event in scan_service.stream_scan(scan_id=scan.id, db=db_session):
        events.append(event)

    assert len(events) == 2
    assert events[0]["event"] == "start"
    assert events[1]["event"] == "complete"

    db_session.refresh(scan)
    assert scan.status == ScanStatus.COMPLETED.value
    assert scan.score == 85
    assert scan.grade == "B"
    assert len(scan.findings) == 1

    # 2. Replay khi đã COMPLETED
    replay_events = []
    async for event in scan_service.stream_scan(scan_id=scan.id, db=db_session):
        replay_events.append(event)

    assert len(replay_events) == 1
    assert replay_events[0]["event"] == "complete"
    assert "Phiên quét đã hoàn tất từ trước" in replay_events[0]["message"]


@pytest.mark.asyncio
async def test_stream_scan_error_handling(
    scan_service: ScanService, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kiểm tra stream_scan bắt ngoại lệ, cập nhật FAILED và yield sự kiện ERROR."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")

    async def mock_stream_error(
        self: Any, url: str, scan_id: str
    ) -> AsyncGenerator[dict[str, Any], None]:
        if False:
            empty_item: dict[str, Any] = {}
            yield empty_item
        raise RuntimeError("Unexpected stream error")


    monkeypatch.setattr(Scanner, "scan_stream", mock_stream_error)

    events = []
    async for event in scan_service.stream_scan(scan_id=scan.id, db=db_session):
        events.append(event)

    assert len(events) == 1
    assert events[0]["event"] == ScanEventType.ERROR.value

    db_session.refresh(scan)
    assert scan.status == ScanStatus.FAILED.value


def test_delete_scan(scan_service: ScanService, db_session: Session) -> None:
    """Kiểm tra xóa scan và cascade xóa findings."""
    scan = scan_service.create_scan(db=db_session, target_url="https://example.com")
    finding = FindingModel(
        scan_id=scan.id,
        module="headers",
        name="test",
        severity="low",
        description="desc",
        remediation="fix",
    )
    db_session.add(finding)
    db_session.commit()

    assert db_session.query(ScanModel).count() == 1
    assert db_session.query(FindingModel).count() == 1

    success = scan_service.delete_scan(db=db_session, scan_id=scan.id)
    assert success is True
    assert db_session.query(ScanModel).count() == 0
    assert db_session.query(FindingModel).count() == 0

    # Xóa lần 2 trả về False vì không tồn tại
    assert scan_service.delete_scan(db=db_session, scan_id=scan.id) is False


def test_list_scans(scan_service: ScanService, db_session: Session) -> None:
    """Kiểm tra list_scans sắp xếp giảm dần theo created_at và phân trang."""
    scan1 = scan_service.create_scan(db=db_session, target_url="https://site1.com")
    scan2 = scan_service.create_scan(db=db_session, target_url="https://site2.com")
    scan3 = scan_service.create_scan(db=db_session, target_url="https://site3.com")

    # Windows's wall-clock resolution (~15ms ticks) can make 3 rapid-fire datetime.now() calls
    # return the SAME value, leaving `ORDER BY created_at DESC` ambiguous between them. Force
    # distinct timestamps so this test asserts a specific order deterministically everywhere.
    base = datetime.now(UTC)
    for offset, scan in enumerate((scan1, scan2, scan3)):
        scan.created_at = base + timedelta(seconds=offset)
    db_session.commit()

    all_scans = scan_service.list_scans(db=db_session, skip=0, limit=10)
    assert len(all_scans) == 3
    # Mới nhất lên đầu
    assert all_scans[0].id == scan3.id
    assert all_scans[1].id == scan2.id
    assert all_scans[2].id == scan1.id

    paged = scan_service.list_scans(db=db_session, skip=1, limit=1)
    assert len(paged) == 1
    assert paged[0].id == scan2.id
