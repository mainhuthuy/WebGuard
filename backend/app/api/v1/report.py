"""API routes for scan report export operations."""

from datetime import datetime, timezone
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, status
from fastapi.responses import HTMLResponse, JSONResponse

from jinja2 import Environment, FileSystemLoader

from app.api.v1.scan import scan_jobs
from app.core.errors import ScanNotFoundException

logger = logging.getLogger("app.api.v1.report")

router = APIRouter(prefix="/report", tags=["Report"])

# Cấu hình Jinja2 template engine
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


class ExportFormat(str, Enum):
    JSON = "json"
    HTML = "html"


@router.get(
    "/{scan_id}/export",
    response_model=None,
    summary="Xuất báo cáo quét bảo mật",
    description="Tải xuống báo cáo kết quả quét dưới định dạng JSON hoặc HTML.",
)
async def export_report(
    scan_id: str,
    format: ExportFormat = Query(
        default=ExportFormat.JSON,
        description="Định dạng xuất báo cáo: 'json' hoặc 'html'",
    ),
) -> JSONResponse | HTMLResponse:
    """Xuất báo cáo kết quả quét theo định dạng yêu cầu."""
    if scan_id not in scan_jobs:
        raise ScanNotFoundException(scan_id=scan_id)

    job = scan_jobs[scan_id]
    findings: list[dict[str, Any]] = job.get("findings") or []
    scoring_data: dict[str, Any] = job.get("scoring") or {}

    # Đếm số lượng findings theo mức độ nghiêm trọng
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        sev = finding.get("severity", "").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

    report_data: dict[str, Any] = {
        "scan_id": scan_id,
        "target_url": job["target_url"],
        "status": job["status"].value if hasattr(job["status"], "value") else str(job["status"]),
        "created_at": str(job["created_at"]),
        "completed_at": str(job["completed_at"]) if job.get("completed_at") else None,
        "total_findings": len(findings),
        "findings": findings,
        "scoring": scoring_data if scoring_data else None,
        "severity_counts": severity_counts,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # --- Xuất JSON ---
    if format == ExportFormat.JSON:
        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="webguard_report_{scan_id[:8]}.json"',
            },
        )

    # --- Xuất HTML ---
    template = jinja_env.get_template("report.html")
    html_content = template.render(**report_data)

    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f'attachment; filename="webguard_report_{scan_id[:8]}.html"',
        },
    )
