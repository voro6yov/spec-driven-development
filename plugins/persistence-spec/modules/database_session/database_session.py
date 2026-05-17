import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from .constants import DBDialect, DBDriver

__all__ = ["DatabaseSession", "metadata"]


metadata = MetaData()


class DatabaseSession:  # noqa: WPS230
    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        database: str,
        dialect: DBDialect = DBDialect.POSTGRES,
        driver: DBDriver = DBDriver.PSYCOPG2,
        metaflags: dict | None = None,
        require_secure_transport: bool = False,
        sslkey: str = "",
        sslcert: str = "",
        sslrootcert: str = "",
        sslmode: str = "verify-full",
        pool_size: int = 10,
    ) -> None:
        engine_url = URL.create(
            drivername=f"{dialect.value}+{driver.value}",
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            query=metaflags if metaflags is not None else {},
        )

        self.engine = create_engine(
            engine_url,
            pool_size=pool_size,
            connect_args=(
                {
                    "sslcert": sslcert,
                    "sslkey": sslkey,
                    "sslmode": sslmode,
                    "sslrootcert": sslrootcert,
                }
                if require_secure_transport
                else {}
            ),
            execution_options={"isolation_level": "REPEATABLE READ"},
        )

        self.session_factory = scoped_session(sessionmaker(bind=self.engine))

        self._logger = logging.getLogger(self.__class__.__name__)

    @contextmanager
    def connect(self) -> Generator[Session, None, None]:
        self.session_factory()
        try:
            yield self.session_factory
        finally:
            self.session_factory.remove()

    @contextmanager
    def connection(self) -> Generator[Session, None, None]:
        self.session_factory()
        try:
            yield self.session_factory
            self.session_factory.commit()
        except Exception as e:
            self.session_factory.rollback()
            raise e
        finally:
            self.session_factory.remove()

    def healthcheck(self):
        with self.connection() as conn:
            conn.execute(text("select 1;"))
