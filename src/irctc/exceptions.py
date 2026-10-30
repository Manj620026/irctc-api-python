"""
irctc.exceptions
~~~~~~~~~~~~~~~~

Typed error hierarchy for the irctc-api client.
"""

from typing import Optional, Any, Dict


class IrctcApiError(Exception):
    """Base exception for all irctc-api errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.code:
            parts.append(f"[code: {self.code}]")
        if self.status_code:
            parts.append(f"[status: {self.status_code}]")
        return " ".join(parts)


class AuthenticationError(IrctcApiError):
    """Raised when authentication fails (HTTP 401). Invalid or missing API key."""
    pass


class InsufficientCreditsError(IrctcApiError):
    """Raised when developer account has zero credits remaining (HTTP 402)."""
    pass


class NotFoundError(IrctcApiError):
    """Raised when the requested train, station, or PNR is not found (HTTP 404)."""
    pass


class RateLimitError(IrctcApiError):
    """Raised when API rate limits are exceeded (HTTP 429)."""
    pass


class ServerError(IrctcApiError):
    """Raised when the upstream railway engine or gateway encounters an internal error (HTTP 500/502/503)."""
    pass


class TimeoutError(IrctcApiError):
    """Raised when a request exceeds the configured network timeout."""
    pass


def map_http_error(
    status_code: int,
    data: Optional[Dict[str, Any]] = None,
    default_msg: Optional[str] = None,
) -> IrctcApiError:
    """Helper to map HTTP status codes and error payloads to typed exceptions."""
    payload = data or {}
    message = (
        payload.get("error")
        or payload.get("message")
        or default_msg
        or f"Request failed with HTTP {status_code}"
    )
    code = payload.get("code")

    if status_code == 401:
        return AuthenticationError(message, code=code, status_code=status_code, details=payload)
    if status_code == 402:
        return InsufficientCreditsError(message, code=code, status_code=status_code, details=payload)
    if status_code == 404:
        return NotFoundError(message, code=code, status_code=status_code, details=payload)
    if status_code == 429:
        return RateLimitError(message, code=code, status_code=status_code, details=payload)
    if status_code in (500, 502, 503, 504):
        return ServerError(message, code=code, status_code=status_code, details=payload)

    return IrctcApiError(message, code=code, status_code=status_code, details=payload)
