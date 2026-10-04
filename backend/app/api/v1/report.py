"""API routes for scan report export operations."""

import logging
from enum import Enum

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.report import report_service

logger = logging.getLogger("app.api.v1.report")

router = APIRouter(prefix="/report", tags=["Report"])


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
    db: Session = Depends(get_db),
) -> JSONResponse | HTMLResponse:
    """Xuất báo cáo kết quả quét theo định dạng yêu cầu qua ReportService."""
    filename = report_service.get_export_filename(
        scan_id=scan_id, format_ext=format.value
    )

    # --- Xuất JSON ---
    if format == ExportFormat.JSON:
        report_data = report_service.generate_json_report(scan_id=scan_id, db=db)
        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # --- Xuất HTML qua Jinja2 template ---
    html_content = report_service.generate_html_report(scan_id=scan_id, db=db)
    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
