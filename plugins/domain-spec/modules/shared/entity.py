from abc import ABCMeta

from .guards import Guard

__all__ = ["Entity"]


class Entity(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):  # noqa: N804
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)  # noqa: WPS117

        cls.guards = [key for key, value in namespace.items() if isinstance(value, Guard)]

        cls.__eq__ = mcs.eq
        cls.__repr__ = mcs.repr
        cls.equals = mcs.equals

        return cls

    @staticmethod
    def eq(entity: "Entity", other: object) -> bool:
        return isinstance(other, entity.__class__) and other.id == entity.id

    @staticmethod
    def repr(entity: "Entity") -> str:
        return "\n".join(
            (
                f"class {entity.__class__.__name__}:",
                *[f"\t{guard} = {getattr(entity, guard)}" for guard in entity.guards],
            ),
        )

    @staticmethod
    def equals(entity: "Entity", other: object) -> bool:
        return isinstance(other, entity.__class__) and all(
            getattr(entity, guard) == getattr(other, guard) for guard in entity.guards
        )
