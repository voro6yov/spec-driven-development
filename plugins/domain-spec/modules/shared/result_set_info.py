from typing import TypedDict

__all__ = ["ResultSetInfo"]


class ResultSetInfo(TypedDict):
    count: int
    offset: int
    limit: int
    total: int
