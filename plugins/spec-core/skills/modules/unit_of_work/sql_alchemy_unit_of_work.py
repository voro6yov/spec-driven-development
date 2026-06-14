from sqlalchemy.orm import Session

# Add DatabaseSession import there

from .abstract_unit_of_work import AbstractUnitOfWork

__all__ = ["SqlAlchemyUnitOfWork"]


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    _session: Session

    def __init__(self, database_session: DatabaseSession) -> None:
        self._database_session = database_session

    def __enter__(self) -> None:
        with self._database_session.connect() as session:
            self._session = session

    def commit(self):
        self._session.commit()

    def rollback(self):
        self._session.rollback()
