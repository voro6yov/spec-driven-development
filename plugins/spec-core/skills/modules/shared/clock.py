from datetime import UTC, datetime

__all__ = ["utc_now"]


def utc_now() -> datetime:
    return datetime.now(UTC)
