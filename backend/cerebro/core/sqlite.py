from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteTransaction:
    """Provide an explicit SQLite transaction boundary."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row

        try:
            connection.execute("BEGIN")
        except Exception:
            connection.close()
            raise

        self._connection = connection
        return connection

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        connection = self._connection

        if connection is None:
            return

        try:
            if exc_type is None:
                connection.commit()
            else:
                connection.rollback()
        finally:
            connection.close()
            self._connection = None
