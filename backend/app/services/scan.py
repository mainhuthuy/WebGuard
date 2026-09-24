"""ScanService — Quản lý toàn bộ vòng đời của một phiên quét bảo mật (Scan Lifecycle).

Cung cấp các nghiệp vụ:
- Khởi tạo phiên quét (pending) và lưu vào Database
- Thực thi quét bất đồng bộ (running -> completed / failed)
- Chạy nền qua Background Task (asyncio.Task)
- Hủy phiên quét đang chạy (cancelled)
- Bắn sự kiện tiến trình qua SSE Stream và lưu kết quả vào DB
- Phân trang lịch sử quét và xóa phiên quét
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import json
import logging
from typing import Any
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.errors import ScanNotFoundException
from app.db.session import SessionLocal
from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.modules.scanner import Scanner
from app.schemas.scan import (
    ScanEventType,
    ScanStatus,
)

logger = logging.getLogger("app.services.scan")


class ScanService:
    """Service layer chịu trách nhiệm điều phối vòng đời của các phiên quét WebGuard."""

    def __init__(self) -> None:
        # Lưu các asyncio.Task đang chạy ngầm trong memory để quản lý và hủy khi cần
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}

    def create_scan(self, db: Session, target_url: str) -> ScanModel:
        """Khởi tạo một bản ghi quét mới với trạng thái pending và lưu vào database."""
        scan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        scan_record = ScanModel(
            id=scan_id,
            target_url=target_url,
            status=ScanStatus.PENDING.value,
            created_at=now,
        )
        db.add(scan_record)
        db.commit()
        db.refresh(scan_record)

        logger.info(f"ScanService: Đã tạo phiên quét mới id={scan_id}, target={target_url}")
        return scan_record

    def get_scan(self, db: Session, scan_id: str) -> ScanModel | None:
        """Truy vấn một phiên quét từ database theo scan_id kèm danh sách findings."""
        return db.query(ScanModel).filter(ScanModel.id == scan_id).first()

    def get_scan_or_404(self, db: Session, scan_id: str) -> ScanModel:
        """Truy vấn phiên quét, nếu không tìm thấy ném ngoại lệ ScanNotFoundException."""
        scan = self.get_scan(db, scan_id)
        if not scan:
            raise ScanNotFoundException(scan_id=scan_id)
        return scan

    async def execute_scan(
        self,
        scan_id: str,
        db: Session | None = None,
    ) -> ScanModel:
        """Thực thi toàn bộ quy trình quét từ đầu đến cuối, cập nhật trạng thái và kết quả vào DB.

        Nếu không truyền db session (ví dụ chạy trong background task), service sẽ tự
        tạo session từ SessionLocal và đóng khi hoàn tất.
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            scan = self.get_scan(db, scan_id)
            if not scan:
                raise ScanNotFoundException(scan_id=scan_id)

            # Nếu scan đã bị hủy trước đó thì dừng lại
            if scan.status == ScanStatus.CANCELLED.value:
                logger.info(f"ScanService: Phiên quét {scan_id} đã bị hủy trước khi chạy.")
                return scan

            # Cập nhật trạng thái đang chạy (running)
            scan.status = ScanStatus.RUNNING.value
            db.commit()
            db.refresh(scan)
            logger.info(f"ScanService: Bắt đầu thực thi quét {scan_id} ({scan.target_url})")

            # Gọi Scanner Orchestrator chạy song song 5 module
            scanner = Scanner()
            scan_result = await scanner.scan(url=scan.target_url)

            # Kiểm tra xem trong lúc quét có bị hủy hay không
            db.refresh(scan)
            if scan.status == ScanStatus.CANCELLED.value:
                logger.info(f"ScanService: Phiên quét {scan_id} đã bị hủy trong quá trình chạy.")
                return scan

            # Hỗ trợ cả dict (từ Scanner.scan) và object ScanResponse
            findings_data: list[Any] = (
                scan_result.get("findings", [])
                if isinstance(scan_result, dict)
                else getattr(scan_result, "findings", [])
            )
            scoring_obj = (
                scan_result.get("scoring", {})
                if isinstance(scan_result, dict)
                else getattr(scan_result, "scoring", {})
            )
            score_val = (
                scoring_obj.get("score")
                if isinstance(scoring_obj, dict)
                else getattr(scoring_obj, "score", None)
            )
            grade_val = (
                scoring_obj.get("grade")
                if isinstance(scoring_obj, dict)
                else getattr(scoring_obj, "grade", None)
            )

            # Lưu các findings vào DB
            for finding in findings_data:
                module_val = (
                    finding.get("module", "unknown")
                    if isinstance(finding, dict)
                    else getattr(finding, "module", "unknown")
                )
                name_val = (
                    finding.get("name", "Unknown Issue")
                    if isinstance(finding, dict)
                    else getattr(finding, "name", "Unknown Issue")
                )
                sev_raw = (
                    finding.get("severity", "low")
                    if isinstance(finding, dict)
                    else getattr(finding, "severity", "low")
                )
                sev_val = (
                    sev_raw.value
                    if hasattr(sev_raw, "value")
                    else str(sev_raw)
                )
                desc_val = (
                    finding.get("description", "")
                    if isinstance(finding, dict)
                    else getattr(finding, "description", "")
                )
                rem_val = (
                    finding.get("remediation", "")
                    if isinstance(finding, dict)
                    else getattr(finding, "remediation", "")
                )
                url_val = (
                    finding.get("url")
                    if isinstance(finding, dict)
                    else getattr(finding, "url", None)
                ) or scan.target_url

                finding_model = FindingModel(
                    scan_id=scan.id,
                    module=module_val,
                    name=name_val,
                    severity=sev_val,
                    description=desc_val,
                    remediation=rem_val,
                    target_url=url_val,
                )
                db.add(finding_model)

            # Cập nhật kết quả chấm điểm và đánh dấu hoàn thành
            scan.score = score_val
            scan.grade = grade_val
            scan.status = ScanStatus.COMPLETED.value
            scan.completed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(scan)
            logger.info(
                f"ScanService: Hoàn tất quét {scan_id} - Score: {scan.score} ({scan.grade}), "
                f"Total findings: {len(findings_data)}"
            )
            return scan


        except asyncio.CancelledError:
            logger.warning(f"ScanService: Quá trình quét {scan_id} bị hủy (CancelledError)")
            scan = self.get_scan(db, scan_id)
            if scan and scan.status != ScanStatus.CANCELLED.value:
                scan.status = ScanStatus.CANCELLED.value
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
            raise

        except Exception as exc:
            logger.exception(f"ScanService: Lỗi sự cố khi quét {scan_id}: {exc}")
            scan = self.get_scan(db, scan_id)
            if scan:
                scan.status = ScanStatus.FAILED.value
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
            raise

        finally:
            if should_close_db and db is not None:
                db.close()

    def start_background_scan(self, scan_id: str) -> asyncio.Task[Any]:
        """Khởi chạy quét bất đồng bộ trong nền (background task) sử dụng asyncio.create_task.

        Theo dõi task trong _active_tasks để hỗ trợ hủy bỏ (cancel) khi cần.
        """
        task = asyncio.create_task(self.execute_scan(scan_id=scan_id))
        self._active_tasks[scan_id] = task

        def _cleanup(t: asyncio.Task[Any]) -> None:
            self._active_tasks.pop(scan_id, None)

        task.add_done_callback(_cleanup)
        logger.info(f"ScanService: Đã khởi chạy background task cho scan_id={scan_id}")
        return task

    def cancel_scan(self, db: Session, scan_id: str) -> bool:
        """Hủy một phiên quét đang ở trạng thái pending hoặc running.

        Trả về True nếu hủy thành công, False nếu phiên quét không tồn tại hoặc đã kết thúc.
        """
        scan = self.get_scan(db, scan_id)
        if not scan:
            return False

        # Không thể hủy nếu phiên quét đã hoàn tất, thất bại hoặc đã hủy
        terminal_statuses = {
            ScanStatus.COMPLETED.value,
            ScanStatus.FAILED.value,
            ScanStatus.CANCELLED.value,
        }
        if scan.status in terminal_statuses:
            logger.warning(
                f"ScanService: Không thể hủy scan {scan_id} vì đang ở trạng thái {scan.status}"
            )
            return False

        # 1. Hủy asyncio Task nếu task đang chạy ngầm
        task = self._active_tasks.get(scan_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"ScanService: Đã gửi tín hiệu cancel tới background task của {scan_id}")

        # 2. Cập nhật trạng thái trong database
        scan.status = ScanStatus.CANCELLED.value
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        logger.info(f"ScanService: Đã đánh dấu phiên quét {scan_id} là CANCELLED")
        return True

    async def stream_scan(
        self,
        scan_id: str,
        db: Session,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Generator hỗ trợ SSE Stream: phát sự kiện từng bước và đồng thời cập nhật DB."""
        scan = self.get_scan_or_404(db, scan_id)

        # Trường hợp 1: Đã hoàn tất từ trước -> Replay lại sự kiện COMPLETE
        if scan.status == ScanStatus.COMPLETED.value:
            findings_data = [
                {
                    "module": f.module,
                    "name": f.name,
                    "severity": f.severity,
                    "description": f.description,
                    "remediation": f.remediation,
                    "url": f.target_url,
                }
                for f in scan.findings
            ]
            scoring_data = {
                "score": scan.score or 0,
                "grade": scan.grade or "F",
                "total_findings": len(findings_data),
            }
            replayed_event = {
                "event": ScanEventType.COMPLETE.value,
                "scan_id": scan_id,
                "progress": 100,
                "message": "Phiên quét đã hoàn tất từ trước.",
                "module": None,
                "findings": findings_data,
                "data": {
                    "url": scan.target_url,
                    "total_findings": len(findings_data),
                    "scoring": scoring_data,
                },
            }
            yield replayed_event
            return

        # Trường hợp 2: Bắt đầu luồng quét và lưu vào DB
        scan.status = ScanStatus.RUNNING.value
        db.commit()
        db.refresh(scan)

        # Lưu task hiện tại vào active tasks để có thể bị cancel nếu client yêu cầu
        current_task = asyncio.current_task()
        if current_task:
            self._active_tasks[scan_id] = current_task

        scanner = Scanner()
        try:
            async for step_event in scanner.scan_stream(url=scan.target_url, scan_id=scan_id):
                # Khi nhận sự kiện hoàn thành từ scanner -> lưu findings và điểm vào DB
                if step_event["event"] == ScanEventType.COMPLETE.value:
                    findings_list = step_event.get("findings") or []
                    for f in findings_list:
                        finding_model = FindingModel(
                            scan_id=scan.id,
                            module=f.get("module", "unknown"),
                            name=f.get("name", "Unknown Issue"),
                            severity=f.get("severity", "low"),
                            description=f.get("description", ""),
                            remediation=f.get("remediation", ""),
                            target_url=f.get("url") or scan.target_url,
                        )
                        db.add(finding_model)

                    event_data = step_event.get("data") or {}
                    scoring = event_data.get("scoring") or {}
                    scan.score = scoring.get("score")
                    scan.grade = scoring.get("grade")
                    scan.status = ScanStatus.COMPLETED.value
                    scan.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(scan)

                yield step_event

        except asyncio.CancelledError:
            logger.warning(f"ScanService: Luồng stream của {scan_id} bị hủy")
            scan.status = ScanStatus.CANCELLED.value
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

        except Exception as exc:
            logger.exception(f"ScanService: Lỗi sự cố khi stream scan_id={scan_id}: {exc}")
            scan.status = ScanStatus.FAILED.value
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()

            empty_findings: list[dict[str, Any]] = []
            error_event: dict[str, Any] = {
                "event": ScanEventType.ERROR.value,
                "scan_id": scan_id,
                "progress": 100,
                "message": f"Quá trình quét gặp sự cố ngoài dự kiến: {exc}",
                "module": None,
                "findings": empty_findings,
                "data": None,
            }
            yield error_event

        finally:
            self._active_tasks.pop(scan_id, None)

    def delete_scan(self, db: Session, scan_id: str) -> bool:
        """Xóa một phiên quét và tự động cascade delete các findings liên quan."""
        scan = self.get_scan(db, scan_id)
        if not scan:
            return False

        # Nếu task đang chạy, hủy task trước
        task = self._active_tasks.get(scan_id)
        if task and not task.done():
            task.cancel()

        db.delete(scan)
        db.commit()

        try:
            from app.api.v1.scan import scan_jobs

            scan_jobs.pop(scan_id, None)
        except ImportError:
            pass

        logger.info(f"ScanService: Đã xóa phiên quét {scan_id}")
        return True


    def list_scans(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ScanModel]:
        """Lấy danh sách các phiên quét, sắp xếp giảm dần theo thời gian tạo."""
        return (
            db.query(ScanModel)
            .order_by(desc(ScanModel.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )


# Singleton instance dùng chung trong ứng dụng
scan_service = ScanService()
