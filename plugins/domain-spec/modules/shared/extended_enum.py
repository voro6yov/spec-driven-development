from enum import Enum, EnumMeta

__all__ = ["ExtendedEnum"]


class ExtendedEnumMeta(EnumMeta):
    def __contains__(cls, item):  # noqa: N805
        return isinstance(item, cls) or item in {v.value for v in cls.__members__.values()}


class ExtendedEnum(str, Enum, metaclass=ExtendedEnumMeta):
    pass
