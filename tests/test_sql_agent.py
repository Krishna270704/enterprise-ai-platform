
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from app.sql_agent import validate_sql
from app.db import select_rows


def test_valid_select_query():
    sql = validate_sql(
        "SELECT COUNT(*) FROM customers"
    )
    assert sql == "SELECT COUNT(*) FROM customers"


def test_valid_query_with_trailing_semicolon():
    sql = validate_sql(
        "SELECT COUNT(*) FROM customers;"
    )
    assert ";" not in sql


def test_reject_insert_query():
    with pytest.raises(ValueError):
        validate_sql(
            "INSERT INTO customers VALUES ('C1')"
        )


def test_reject_delete_query():
    with pytest.raises(ValueError):
        validate_sql(
            "DELETE FROM customers"
        )


def test_reject_unknown_table():
    with pytest.raises(ValueError):
        validate_sql(
            "SELECT * FROM unknown_table"
        )


def test_reject_multiple_statements():
    with pytest.raises(ValueError):
        validate_sql(
            "SELECT * FROM customers; DROP TABLE customers"
        )


def test_database_execution_rejects_non_select():
    with pytest.raises(ValueError, match="Only SELECT"):
        select_rows("UPDATE customers SET name = name")
