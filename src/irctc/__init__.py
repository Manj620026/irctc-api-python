"""
irctc
~~~~~

Official Python SDK for the Indian Railways API (https://irctc.dev).
Fast, zero-dependency client for PNR, Live Train GPS, Timetables, and Fares.
"""

from .client import RailEngine, IrctcApi, __version__
from .exceptions import (
    IrctcApiError,
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

__all__ = [
    "RailEngine",
    "IrctcApi",
    "IrctcApiError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "__version__",
]
