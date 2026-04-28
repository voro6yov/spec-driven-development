import abc

__all__ = ["AbstractQueryContext"]


class AbstractQueryContext:

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError
