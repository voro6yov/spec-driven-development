from dataclasses import dataclass

__all__ = ["Pagination"]


@dataclass
class Pagination:
    limit: int
    offset: int

    @property
    def first_element_index(self) -> int:
        return self.limit * self.offset

    @property
    def last_element_index(self) -> int:
        return self.first_element_index + self.limit
