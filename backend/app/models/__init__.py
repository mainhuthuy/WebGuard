"""Export all models for easy importing."""

from app.models.finding import FindingModel
from app.models.scan import ScanModel

__all__ = ["ScanModel", "FindingModel"]
