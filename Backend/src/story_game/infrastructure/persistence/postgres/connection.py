"""Connection creation kept outside the persistence readers and writers."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row


class PostgresConnectionFactory:
    """Create independent PostgreSQL connections for one unit of work."""

    def __init__(self, dsn: str) -> None:
        if not dsn.strip():
            raise ValueError("Ein PostgreSQL-DSN darf nicht leer sein")
        self.dsn = dsn

    def connect(self) -> psycopg.Connection[Any]:
        """Open a connection whose rows are addressable by column name."""
        return psycopg.connect(self.dsn, row_factory=dict_row)
