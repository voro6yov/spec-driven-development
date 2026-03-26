from typing import Optional
from uuid import uuid4

from .guards import Guard, ImmutableCheck

__all__ = ["EntityId"]


class EntityId:
    value = Guard[str](str, ImmutableCheck())

    def __init__(self, value: Optional[str] = None) -> None:
        self.value = value if value is not None else uuid4().hex

    def __call__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<EntityId: {self.value}>"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.value == other.value
