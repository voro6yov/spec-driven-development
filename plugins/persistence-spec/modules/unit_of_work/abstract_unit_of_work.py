import abc

__all__ = ["AbstractUnitOfWork"]


class AbstractUnitOfWork(abc.ABC):

    def __exit__(self, *args):
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError
