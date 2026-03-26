from typing import TypedDict

from .result_set_info import ResultSetInfo

__all__ = ["PaginatedResultMetadataInfo"]


class PaginatedResultMetadataInfo(TypedDict):
    result_set: ResultSetInfo
