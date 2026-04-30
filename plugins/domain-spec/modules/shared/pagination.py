from dataclasses import dataclass

__all__ = ["Pagination"]


@dataclass
class Pagination:
    page: int
    per_page: int

    @property
    def first_element_index(self) -> int:
        return self.page * self.per_page

    @property
    def last_element_index(self) -> int:
        return self.first_element_index + self.page
