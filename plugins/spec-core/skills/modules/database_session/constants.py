from enum import Enum

__all__ = ["DBDialect", "DBDriver"]


class DBDialect(Enum):
    POSTGRES = "postgresql"
    MSSQL = "mssql"


class DBDriver(Enum):
    PSYCOPG2 = "psycopg2"
    PG8000 = "pg8000"
    PYTDS = "pytds"
    PYODBC = "pyodbc"
