"""Unit tests for HistoryService."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base
from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.schemas.scan import ScanStatus
from app.services.history import HistoryService


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
def history_service() -> HistoryService:
    """Khởi tạo một instance HistoryService cho test."""
    return HistoryService()


def test_get_history_empty_db(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra khi database chưa có dữ liệu thì trả về phân trang rỗng an toàn."""
    res = history_service.get_history(db=db_session, page=1, page_size=10)

    assert res.total == 0
    assert len(res.items) == 0
    assert res.page == 1
    assert res.page_size == 10
    assert res.total_pages == 0
    assert res.has_next is False
    assert res.has_prev is False


def test_get_history_pagination(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra phân trang chính xác khi có nhiều bản ghi."""
    now = datetime.now(UTC)
    for i in range(15):
        scan = ScanModel(
            id=str(uuid.uuid4()),
            target_url=f"https://example{i}.com",
            status="completed",
            created_at=now + timedelta(minutes=i),
        )
        db_session.add(scan)
    db_session.commit()

    # Trang 1: 10 bản ghi
    page1 = history_service.get_history(db=db_session, page=1, page_size=10)
    assert page1.total == 15
    assert len(page1.items) == 10
    assert page1.page == 1
    assert page1.total_pages == 2
    assert page1.has_next is True
    assert page1.has_prev is False

    # Trang 2: 5 bản ghi còn lại
    page2 = history_service.get_history(db=db_session, page=2, page_size=10)
    assert page2.total == 15
    assert len(page2.items) == 5
    assert page2.page == 2
    assert page2.has_next is False
    assert page2.has_prev is True


def test_get_history_filters(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra các bộ lọc search_url, status, grade và khoảng thời gian."""
    now = datetime.now(UTC)

    scan1 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://alpha-security.com",
        status="completed",
        grade="A",
        score=95,
        created_at=now - timedelta(days=2),
    )
    scan2 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://beta-vulnerable.com",
        status="completed",
        grade="F",
        score=40,
        created_at=now - timedelta(days=1),
    )
    scan3 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://gamma-pending.com",
        status="pending",
        created_at=now,
    )
    db_session.add_all([scan1, scan2, scan3])
    db_session.commit()

    # 1. Tìm theo URL
    res_url = history_service.get_history(
        db=db_session, search_url="alpha"
    )
    assert res_url.total == 1
    assert res_url.items[0].target_url == "https://alpha-security.com"

    # 2. Lọc theo Status
    res_status = history_service.get_history(
        db=db_session, status="pending"
    )
    assert res_status.total == 1
    assert res_status.items[0].status == ScanStatus.PENDING

    # 3. Lọc theo Grade
    res_grade = history_service.get_history(
        db=db_session, grade="F"
    )
    assert res_grade.total == 1
    assert res_grade.items[0].grade == "F"

    # 4. Lọc theo Date range
    from_date = now - timedelta(days=1, hours=12)
    res_date = history_service.get_history(
        db=db_session, from_date=from_date
    )
    assert res_date.total == 2  # scan2 và scan3


def test_get_history_sorting(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra sắp xếp theo điểm số score tăng dần và giảm dần."""
    scan1 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://low-score.com",
        status="completed",
        score=50,
        grade="D",
        created_at=datetime.now(UTC),
    )
    scan2 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://high-score.com",
        status="completed",
        score=99,
        grade="A+",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([scan1, scan2])
    db_session.commit()

    # Sắp xếp score tăng dần
    res_asc = history_service.get_history(
        db=db_session, sort_by="score", sort_order="asc"
    )
    assert res_asc.items[0].score == 50
    assert res_asc.items[1].score == 99

    # Sắp xếp score giảm dần
    res_desc = history_service.get_history(
        db=db_session, sort_by="score", sort_order="desc"
    )
    assert res_desc.items[0].score == 99
    assert res_desc.items[1].score == 50


def test_get_stats(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra tính toán các chỉ số thống kê tổng quan lịch sử."""
    scan1 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://site1.com",
        status="completed",
        score=90,
        grade="A",
        created_at=datetime.now(UTC),
    )
    scan2 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://site2.com",
        status="completed",
        score=70,
        grade="C",
        created_at=datetime.now(UTC),
    )
    scan3 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://site3.com",
        status="failed",
        created_at=datetime.now(UTC),
    )
    scan4 = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://site4.com",
        status="cancelled",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([scan1, scan2, scan3, scan4])
    db_session.commit()

    stats = history_service.get_stats(db=db_session)
    assert stats.total_scans == 4
    assert stats.completed_scans == 2
    assert stats.failed_scans == 1
    assert stats.cancelled_scans == 1
    assert stats.average_score == 80.0
    assert stats.grade_distribution["A"] == 1
    assert stats.grade_distribution["C"] == 1
    assert stats.grade_distribution["B"] == 0


def test_delete_history_item(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra xóa 1 bản ghi lịch sử và cascade xóa findings."""
    scan_id = str(uuid.uuid4())
    scan = ScanModel(
        id=scan_id,
        target_url="https://delete-me.com",
        status="completed",
        created_at=datetime.now(UTC),
    )
    finding = FindingModel(
        scan_id=scan_id,
        module="headers",
        name="test",
        severity="low",
        description="desc",
        remediation="fix",
    )
    scan.findings.append(finding)
    db_session.add(scan)
    db_session.commit()

    assert db_session.query(ScanModel).count() == 1
    assert db_session.query(FindingModel).count() == 1

    deleted = history_service.delete_history_item(db=db_session, scan_id=scan_id)
    assert deleted is True
    assert db_session.query(ScanModel).count() == 0
    assert db_session.query(FindingModel).count() == 0

    # Xóa lần 2 trả về False
    assert (
        history_service.delete_history_item(db=db_session, scan_id=scan_id) is False
    )


def test_clear_history_all_and_older_than(
    history_service: HistoryService, db_session: Session
) -> None:
    """Kiểm tra xóa toàn bộ hoặc xóa các bản ghi cũ hơn N ngày."""
    now = datetime.now(UTC)
    old_scan = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://old.com",
        status="completed",
        created_at=now - timedelta(days=10),
    )
    recent_scan = ScanModel(
        id=str(uuid.uuid4()),
        target_url="https://recent.com",
        status="completed",
        created_at=now - timedelta(days=1),
    )
    db_session.add_all([old_scan, recent_scan])
    db_session.commit()

    # Xóa các bản ghi cũ hơn 7 ngày -> Chỉ old_scan bị xóa
    deleted_old = history_service.clear_history(
        db=db_session, older_than_days=7
    )
    assert deleted_old == 1
    remaining_scan = db_session.query(ScanModel).first()
    assert remaining_scan is not None
    assert remaining_scan.id == recent_scan.id


    # Xóa toàn bộ
    deleted_all = history_service.clear_history(db=db_session)
    assert deleted_all == 1
    assert db_session.query(ScanModel).count() == 0
