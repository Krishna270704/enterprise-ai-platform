
import re

import psycopg2
from psycopg2.extras import RealDictCursor
from .config import DATABASE_URL


def connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Configure backend/.env")

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )


def init_db():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            segment TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT,
            department TEXT,
            city TEXT,
            salary NUMERIC
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            price NUMERIC
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT REFERENCES customers(customer_id),
            order_date DATE,
            status TEXT,
            city TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sales (
            sale_id TEXT PRIMARY KEY,
            order_id TEXT REFERENCES orders(order_id),
            product_id TEXT REFERENCES products(product_id),
            quantity INT,
            revenue NUMERIC,
            sale_date DATE,
            city TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS inventory (
            product_id TEXT PRIMARY KEY REFERENCES products(product_id),
            warehouse TEXT,
            stock INT,
            reorder_level INT
        )
        """
    ]

    with connect() as conn:
        with conn.cursor() as cur:
            for sql in statements:
                cur.execute(sql)
        conn.commit()


def select_rows(sql, params=None):
    statement = sql.strip()
    if not re.match(r"(?is)^select\b", statement):
        raise ValueError("Only SELECT queries are permitted.")
    if ";" in statement.rstrip(";") or "--" in statement or "/*" in statement:
        raise ValueError("Only one read-only SELECT statement is permitted.")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            conn.commit()
            return []
