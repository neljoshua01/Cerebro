from __future__ import annotations

import sqlite3

import pytest

from cerebro.core.sqlite import SqliteTransaction


def create_table(database_path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE records (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )


def test_transaction_commits_successful_writes(tmp_path) -> None:
    database_path = tmp_path / "transaction.sqlite3"
    create_table(database_path)

    with SqliteTransaction(database_path) as connection:
        connection.execute(
            "INSERT INTO records (value) VALUES (?)",
            ("committed",),
        )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT value FROM records"
        ).fetchone()

    assert row == ("committed",)


def test_transaction_rolls_back_on_exception(tmp_path) -> None:
    database_path = tmp_path / "transaction.sqlite3"
    create_table(database_path)

    with pytest.raises(RuntimeError, match="force rollback"):
        with SqliteTransaction(database_path) as connection:
            connection.execute(
                "INSERT INTO records (value) VALUES (?)",
                ("rolled back",),
            )
            raise RuntimeError("force rollback")

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT value FROM records"
        ).fetchone()

    assert row is None


def test_transaction_can_commit_multiple_writes_atomically(tmp_path) -> None:
    database_path = tmp_path / "transaction.sqlite3"
    create_table(database_path)

    with SqliteTransaction(database_path) as connection:
        connection.execute(
            "INSERT INTO records (value) VALUES (?)",
            ("first",),
        )
        connection.execute(
            "INSERT INTO records (value) VALUES (?)",
            ("second",),
        )

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT value FROM records ORDER BY id"
        ).fetchall()

    assert rows == [("first",), ("second",)]


def test_transaction_rolls_back_all_writes_when_later_write_fails(
    tmp_path,
) -> None:
    database_path = tmp_path / "transaction.sqlite3"
    create_table(database_path)

    with pytest.raises(sqlite3.IntegrityError):
        with SqliteTransaction(database_path) as connection:
            connection.execute(
                "INSERT INTO records (id, value) VALUES (?, ?)",
                (1, "first"),
            )
            connection.execute(
                "INSERT INTO records (id, value) VALUES (?, ?)",
                (1, "duplicate"),
            )

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id, value FROM records"
        ).fetchall()

    assert rows == []
