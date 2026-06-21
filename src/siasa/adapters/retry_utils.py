"""Shared retry utilities for GDELT adapters (AP-07 hardening)."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.error import URLError


def _retry_delay_seconds(exc: Exception, default_delay: float, now: datetime) -> float:
    """Calculate retry delay, respecting Retry-After headers on 429/5xx responses."""
    code = getattr(exc, 'code', None)
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        headers = getattr(exc, 'headers', None)
        if headers is not None:
            retry_after = headers.get('Retry-After') if hasattr(headers, 'get') else None
            if retry_after is not None:
                try:
                    return max(default_delay, float(retry_after))
                except (TypeError, ValueError):
                    try:
                        retry_at = parsedate_to_datetime(str(retry_after))
                    except (TypeError, ValueError, IndexError, OverflowError):
                        return default_delay
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=UTC)
                    seconds_until_retry = max(0.0, (retry_at - now).total_seconds())
                    return max(default_delay, seconds_until_retry)
    return default_delay


def is_retryable_error(exc: Exception) -> bool:
    """Return True for HTTP 429, 5xx, TimeoutError, ConnectionError, URLError."""
    code = getattr(exc, 'code', None)
    if isinstance(code, int):
        if code == 429:
            return True
        if 500 <= code < 600:
            return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, ConnectionError):
        return True
    if isinstance(exc, URLError):
        return True
    return False
