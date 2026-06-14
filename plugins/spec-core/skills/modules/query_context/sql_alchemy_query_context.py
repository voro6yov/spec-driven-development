from sqlalchemy.orm import Session

# Add DatabaseSession import there

from .abstract_query_context import AbstractQueryContext

__all__ = ["SqlAlchemyQueryContext"]


class SqlAlchemyQueryContext(AbstractQueryContext):
    _session: Session

    def __init__(self, database_session: DatabaseSession):
        self._database_session = database_session

    def __enter__(self):
        with self._database_session.connect() as session:
            self._session = session

    def __exit__(self, exc_type, exc_value, traceback):
        self._database_session.session_factory.remove()

    def close(self):
        self._database_session.session_factory.remove()
