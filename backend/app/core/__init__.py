"""Core module providing configuration, logging, exceptions, and middlewares."""

from app.core.config import Settings, get_settings
from app.core.errors import (
    InvalidTargetException,
    RateLimitExceededException,
    ScanExecutionException,
    ScanNotFoundException,
    WebGuardException,
    register_exception_handlers,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.security import assert_public_target

__all__ = [
    "Settings",
    "get_settings",
    "setup_logging",
    "RequestLoggingMiddleware",
    "WebGuardException",
    "ScanNotFoundException",
    "InvalidTargetException",
    "ScanExecutionException",
    "RateLimitExceededException",
    "register_exception_handlers",
    "assert_public_target",
]
