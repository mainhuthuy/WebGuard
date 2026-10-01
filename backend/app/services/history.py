"""HistoryService — Quản lý truy vấn, lọc, phân trang và thống kê lịch sử quét an ninh."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.schemas.history import (
    HistoryDeleteResponse,
    ScanHistoryItem,
    ScanHistoryResponse,
    ScanHistoryStats,
)
from app.schemas.scan import ScanStatus

logger = logging.getLogger("app.services.history")


class HistoryService:
    """Service layer chuyên trách quản lý lịch sử quét bảo mật trong WebGuard."""

    def get_history(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search_url: str | None = None,
        status: str | None = None,
        grade: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> ScanHistoryResponse:
        """Truy vấn danh sách các lần quét với bộ lọc tìm kiếm, sắp xếp và phân trang."""
        query = db.query(ScanModel).options(joinedload(ScanModel.findings))

        # 1. Bộ lọc tìm kiếm theo URL (không phân biệt hoa thường)
        if search_url and search_url.strip():
            query = query.filter(
                ScanModel.target_url.ilike(f"%{search_url.strip()}%")
            )

        # 2. Bộ lọc theo trạng thái (status)
        if status and status.strip():
            query = query.filter(ScanModel.status == status.strip().lower())

        # 3. Bộ lọc theo xếp hạng an ninh (grade)
        if grade and grade.strip():
            query = query.filter(ScanModel.grade == grade.strip().upper())

        # 4. Bộ lọc theo khoảng thời gian tạo
        if from_date:
            query = query.filter(ScanModel.created_at >= from_date)
        if to_date:
            query = query.filter(ScanModel.created_at <= to_date)

        # 5. Đếm tổng số bản ghi thỏa điều kiện lọc
        total = query.count()

        # 6. Sắp xếp kết quả (Sort)
        sort_column = (
            ScanModel.score if sort_by.lower() == "score" else ScanModel.created_at
        )
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 7. Tính toán phân trang (Pagination)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        records = query.offset(offset).limit(page_size).all()

        # 8. Đóng gói danh sách item trả về
        items: list[ScanHistoryItem] = []
        for scan in records:
            duration_seconds: float | None = None
            if scan.completed_at and scan.created_at:
                duration_seconds = round(
                    (scan.completed_at - scan.created_at).total_seconds(), 2
                )

            # Đảm bảo status chuyển đổi sang enum an toàn
            try:
                status_enum = ScanStatus(scan.status)
            except ValueError:
                status_enum = ScanStatus.PENDING

            items.append(
                ScanHistoryItem(
                    id=scan.id,
                    target_url=scan.target_url,
                    status=status_enum,
                    mode=scan.mode if scan.mode in ("quick", "full") else "full",
                    score=scan.score,
                    grade=scan.grade,
                    total_findings=len(scan.findings),
                    created_at=scan.created_at,
                    completed_at=scan.completed_at,
                    duration_seconds=duration_seconds,
                )
            )

        has_next = page < total_pages
        has_prev = page > 1 and total_pages > 0

        return ScanHistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    def get_stats(self, db: Session) -> ScanHistoryStats:
        """Tổng hợp các chỉ số thống kê hiệu năng và kết quả các phiên quét."""
        total_scans = db.query(func.count(ScanModel.id)).scalar() or 0

        completed_scans = (
            db.query(func.count(ScanModel.id))
            .filter(ScanModel.status == ScanStatus.COMPLETED.value)
            .scalar()
            or 0
        )
        failed_scans = (
            db.query(func.count(ScanModel.id))
            .filter(ScanModel.status == ScanStatus.FAILED.value)
            .scalar()
            or 0
        )
        cancelled_scans = (
            db.query(func.count(ScanModel.id))
            .filter(ScanModel.status == ScanStatus.CANCELLED.value)
            .scalar()
            or 0
        )

        avg_score_raw = (
            db.query(func.avg(ScanModel.score))
            .filter(ScanModel.score.isnot(None))
            .scalar()
        )
        average_score = (
            round(float(avg_score_raw), 1) if avg_score_raw is not None else None
        )

        # Phân bố xếp hạng grade: A+, A, B, C, D, F
        grade_distribution: dict[str, int] = {
            "A+": 0,
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
            "F": 0,
        }
        grade_counts = (
            db.query(ScanModel.grade, func.count(ScanModel.id))
            .filter(ScanModel.grade.isnot(None))
            .group_by(ScanModel.grade)
            .all()
        )
        for g, count in grade_counts:
            if g and g in grade_distribution:
                grade_distribution[g] = count

        return ScanHistoryStats(
            total_scans=total_scans,
            completed_scans=completed_scans,
            failed_scans=failed_scans,
            cancelled_scans=cancelled_scans,
            average_score=average_score,
            grade_distribution=grade_distribution,
        )

    def delete_history_item(self, db: Session, scan_id: str) -> bool:
        """Xóa một bản ghi phiên quét trong DB (tự động cascade xóa findings con)."""
        scan = db.query(ScanModel).filter(ScanModel.id == scan_id).first()
        if not scan:
            return False

        db.delete(scan)
        db.commit()

        # Dọn dẹp cache in-memory nếu có
        try:
            from app.api.v1.scan import scan_jobs

            scan_jobs.pop(scan_id, None)
        except ImportError:
            pass

        logger.info(f"HistoryService: Đã xóa bản ghi quét {scan_id}")
        return True

    def clear_history(
        self,
        db: Session,
        older_than_days: int | None = None,
    ) -> int:
        """Dọn dẹp lịch sử quét. Nếu truyền older_than_days thì chỉ xóa các bản ghi cũ hơn."""
        query = db.query(ScanModel)
        if older_than_days is not None and older_than_days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=older_than_days
            )
            query = query.filter(ScanModel.created_at < cutoff_date)

        scans_to_delete = query.all()
        count = len(scans_to_delete)
        for scan in scans_to_delete:
            db.delete(scan)
            try:
                from app.api.v1.scan import scan_jobs

                scan_jobs.pop(scan.id, None)
            except ImportError:
                pass

        db.commit()
        logger.info(f"HistoryService: Đã dọn dẹp {count} bản ghi lịch sử")
        return count



# Singleton instance dùng chung
history_service = HistoryService()
