from enum import Enum
from pydantic import BaseModel, HttpUrl

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ScanRequest(BaseModel):
    url: HttpUrl  # Pydantic tự động kiểm tra định dạng URL (phải bắt đầu bằng http:// hoặc https://)

class Finding(BaseModel):
    module: str
    name: str
    severity: SeverityLevel
    description: str
    remediation: str
    url: str | None = None

class ScoringResult(BaseModel):
    score: int
    grade: str
    total_findings: int

class ScanResponse(BaseModel):
    url: str
    total_findings: int
    findings: list[Finding]
    scoring: ScoringResult