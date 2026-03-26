__all__ = ["AttributeName"]


class AttributeName:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def public(self) -> str:
        return self._name

    @property
    def private(self) -> str:
        return f"_{self._name}"
