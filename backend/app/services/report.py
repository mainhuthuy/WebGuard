"""ReportService — Xử lý nghiệp vụ tạo và xuất báo cáo kết quả quét (JSON / HTML).

Nhiệm vụ:
- Thu thập và chuẩn hóa dữ liệu từ Database (hoặc bộ nhớ cache)
- Thống kê phân loại lỗ hổng theo mức độ nghiêm trọng (Severity Counts)
- Tính toán thời gian quét (Duration)
- Render template HTML chuyên nghiệp bằng Jinja2 Engine
- Đóng gói dữ liệu xuất báo cáo dưới định dạng JSON
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.core.errors import ScanNotFoundException
from app.models.finding import FindingModel
from app.models.scan import ScanModel
from app.services.scan import scan_service

logger = logging.getLogger("app.services.report")

# Đường dẫn thư mục chứa template Jinja2
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


class ReportService:
    """Service layer chuyên trách tổng hợp và xuất báo cáo kết quả an ninh WebGuard."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

    def get_report_data(
        self,
        scan_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Thu thập dữ liệu đầy đủ của phiên quét từ Database (hoặc fallback cache).

        Trả về dictionary chuẩn hóa bao gồm: thông tin quét, findings, điểm số,
        bảng thống kê mức độ nghiêm trọng và thời điểm tạo báo cáo.
        """
        scan: ScanModel | None = None
        if db is not None:
            scan = scan_service.get_scan(db, scan_id)

        # Fallback lấy từ scan_jobs in-memory nếu DB chưa có
        if scan is None:
            from app.api.v1.scan import scan_jobs

            if scan_id not in scan_jobs:
                raise ScanNotFoundException(scan_id=scan_id)

            job = scan_jobs[scan_id]
            target_url = job["target_url"]
            status_val = (
                job["status"].value
                if hasattr(job["status"], "value")
                else str(job["status"])
            )
            created_at = job["created_at"]
            completed_at = job.get("completed_at")
            findings_raw = job.get("findings") or []
            scoring_raw = job.get("scoring") or {}

            findings = [
                {
                    "module": f.get("module", "unknown"),
                    "name": f.get("name", "Unknown Issue"),
                    "severity": f.get("severity", "low").lower(),
                    "description": f.get("description", ""),
                    "remediation": f.get("remediation", ""),
                    "url": f.get("url") or target_url,
                }
                for f in findings_raw
            ]
            scoring = scoring_raw if scoring_raw else None
        else:
            target_url = scan.target_url
            status_val = scan.status
            created_at = scan.created_at
            completed_at = scan.completed_at

            findings = [
                {
                    "module": f.module,
                    "name": f.name,
                    "severity": f.severity.lower(),
                    "description": f.description,
                    "remediation": f.remediation,
                    "url": f.target_url or target_url,
                }
                for f in scan.findings
            ]

            if scan.score is not None and scan.grade is not None:
                scoring = {
                    "score": scan.score,
                    "grade": scan.grade,
                    "total_findings": len(findings),
                }
            else:
                scoring = None

        # Đếm số lượng findings theo mức độ nghiêm trọng
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            sev = finding.get("severity", "").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1

        # Tính toán thời lượng quét (duration in seconds) nếu có completed_at
        duration_seconds: float | None = None
        if completed_at and created_at:
            duration_seconds = round(
                (completed_at - created_at).total_seconds(), 2
            )

        now_utc = datetime.now(timezone.utc)

        return {
            "scan_id": scan_id,
            "target_url": target_url,
            "status": status_val,
            "created_at": str(created_at),
            "completed_at": str(completed_at) if completed_at else None,
            "duration_seconds": duration_seconds,
            "total_findings": len(findings),
            "findings": findings,
            "scoring": scoring,
            "severity_counts": severity_counts,
            "generated_at": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    def generate_json_report(
        self,
        scan_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Tạo báo cáo dưới định dạng JSON."""
        return self.get_report_data(scan_id=scan_id, db=db)

    def generate_html_report(
        self,
        scan_id: str,
        db: Session | None = None,
    ) -> str:
        """Render báo cáo dưới định dạng HTML sử dụng Jinja2 template."""
        report_data = self.get_report_data(scan_id=scan_id, db=db)
        template = self.jinja_env.get_template("report.html")
        return template.render(**report_data)

    @staticmethod
    def get_export_filename(scan_id: str, format_ext: str) -> str:
        """Sinh tên file tải về chuẩn format: webguard_report_<short_id>.<ext>."""
        short_id = scan_id[:8] if len(scan_id) >= 8 else scan_id
        return f"webguard_report_{short_id}.{format_ext.lower()}"


# Singleton instance dùng chung
report_service = ReportService()
