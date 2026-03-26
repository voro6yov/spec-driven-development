from typing import Any, Generic, Optional, Type, TypeVar

from .attribute_name import AttributeName
from .checks import Check, NoneCheck, TypeCheck

__all__ = ["Guard"]

T = TypeVar("T")


class Guard(Generic[T]):
    def __init__(self, type_: Type[Any], *checks: Check[T]) -> None:
        self._default_checks: list[Check[T]] = [NoneCheck(), TypeCheck(type_)]
        self._checks = checks

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = AttributeName(name)

    def __get__(self, domain_obj: Any, objtype: Optional[Any] = None) -> T:
        try:
            return getattr(domain_obj, self.name.private)
        except AttributeError:
            return None

    def __set__(self, domain_obj: Any, value: T) -> None:
        self.validate(domain_obj, value)
        setattr(domain_obj, self.name.private, value)

    def validate(self, domain_obj: Any, value: T) -> None:
        for default_check in self._default_checks:
            default_check.is_correct(domain_obj, value, self.name)

        for check in self._checks:
            check.is_correct(domain_obj, value, self.name)

    def __delete__(self, domain_obj: Any) -> None:  # noqa: WPS603
        if hasattr(domain_obj, self.name.private):
            delattr(domain_obj, self.name.private)
