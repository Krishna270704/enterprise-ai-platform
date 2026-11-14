
import re

from groq import Groq

from .config import GROQ_API_KEY, GROQ_MODEL
from .db import select_rows


SCHEMA = """
customers(
    customer_id, name, city, segment
);

employees(
    employee_id, name, department, city, salary
);

products(
    product_id, name, category, price
);

orders(
    order_id, customer_id, order_date, status, city
);

sales(
    sale_id, order_id, product_id, quantity,
    revenue, sale_date, city
);

inventory(
    product_id, warehouse, stock, reorder_level
);
"""

DATABASE_RULES = """
IMPORTANT DATABASE FACTS:

1. The valid orders.status values are:
   - Cancelled
   - Delivered
   - Processing

2. There is NO 'completed' status.

3. There is NO 'refunded' status.

4. There is no dedicated refunds table or refund_amount column.

5. Never invent refund transactions, refund amounts,
   refund rates, or refund dates.

6. If asked for refund information, explain that the
   current schema does not contain sufficient refund data.

7. Total recorded revenue can be calculated from sales.revenue.

8. Delivered-order revenue must be calculated by joining
   orders and sales and filtering orders.status = 'Delivered'.

9. Cancelled-order and Processing-order revenue must not
   be presented as delivered revenue.

10. Currency is not defined in the database.
    Never assume INR, USD, or another currency.

11. Use only the supplied tables and columns.
"""


ALLOWED_TABLES = {
    "customers",
    "employees",
    "products",
    "orders",
    "sales",
    "inventory",
}

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter",
    "truncate", "create", "grant", "revoke", "copy",
    "execute", "call", "merge", "vacuum", "analyze",
    "refresh", "comment", "do", "set", "reset",
    "prepare", "deallocate", "listen", "notify",
}


def validate_sql(sql: str) -> str:
    """Conservatively validate generated read-only SQL."""

    sql = sql.strip()

    # Remove only common Markdown SQL fences.
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.I)
    sql = re.sub(r"\s*```$", "", sql)

    if not sql:
        raise ValueError("Generated SQL is empty.")

    # Permit exactly one SELECT statement.
    if not re.match(r"(?is)^select\b", sql):
        raise ValueError("Only SELECT queries are permitted.")

    # Allow one optional trailing semicolon.
    sql = sql.rstrip()

    if sql.endswith(";"):
        sql = sql[:-1].rstrip()

    # Reject internal semicolons and SQL comments.
    if ";" in sql or "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("Multiple statements and SQL comments are not permitted.")

    # Reject dangerous SQL keywords.
    tokens = re.findall(r"\b[a-z_][a-z0-9_]*\b", sql.lower())

    if any(token in FORBIDDEN_KEYWORDS for token in tokens):
        raise ValueError("Unsafe SQL keyword detected.")

    # Block potentially unsafe functions and database access.
    blocked_patterns = [
        r"\bpg_[a-z0-9_]*\s*\(",
        r"\blo[a-z0-9_]*\s*\(",
        r"\bdblink\s*\(",
        r"\bdblink_exec\s*\(",
        r"\bset_config\s*\(",
        r"\bcurrent_setting\s*\(",
        r"\binformation_schema\b",
        r"\bpg_catalog\b",
        r"\bfor\s+(update|share)\b",
        r"\binto\b",
    ]

    for pattern in blocked_patterns:
        if re.search(pattern, sql, flags=re.I):
            raise ValueError("Potentially unsafe SQL expression detected.")

    # Check table references against the project schema.
    table_references = re.findall(
        r"\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)",
        sql,
        flags=re.I,
    )

    if not table_references:
        raise ValueError("Query must reference an approved database table.")

    for table in table_references:
        if table.lower() not in ALLOWED_TABLES:
            raise ValueError(f"Table not permitted: {table}")

    return sql



def generate_sql(question: str) -> str:
    q = question.lower()

    # Only block questions that actually request refund calculations.
    refund_terms = [
        "refund rate", "refund amount", "total refunds",
        "refunded orders", "refund percentage"
    ]

    database_terms = [
        "customer", "employee", "product", "inventory",
        "stock", "order", "revenue", "sales"
    ]

    asks_for_refunds = any(term in q for term in refund_terms)

    if asks_for_refunds and not any(term in q for term in database_terms):
        raise ValueError(
            "Refund information is unavailable in the current database."
        )

    if not GROQ_API_KEY:
        raise RuntimeError("Set GROQ_API_KEY in backend/.env")

    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""
Generate exactly one PostgreSQL SELECT statement.

The question may contain document-related requests.
Ignore those parts and generate SQL only for the database-related part.

SCHEMA:
{SCHEMA}

DATABASE RULES:
{DATABASE_RULES}

Requirements:
- First SQL keyword must be SELECT.
- Use only the supplied tables and columns.
- Use correct joins.
- Never invent schema fields.
- Never calculate refunds.
- Return SQL only, without Markdown or explanation.
- For a general question about total revenue or monthly sales,
  include ALL records from the sales table.
- Do NOT filter by orders.status unless the user explicitly
  asks for Delivered, Cancelled, or Processing orders.
- For general monthly sales trends, aggregate sales.revenue
  grouped by sale_date month.
- Only apply status filters when explicitly requested.

USER QUESTION:
{question}
"""

    messages = [
        {
            "role": "system",
            "content": "Return only one valid PostgreSQL SELECT statement."
        },
        {"role": "user", "content": prompt}
    ]

    for attempt in range(2):
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0
        )

        raw_sql = response.choices[0].message.content or ""

        try:
            return validate_sql(raw_sql)
        except ValueError as error:
            if attempt == 1:
                raise

            messages.extend([
                {"role": "assistant", "content": raw_sql},
                {
                    "role": "user",
                    "content": (
                        f"Validation failed: {error}. "
                        "Return one corrected SELECT statement only."
                    )
                }
            ])

    raise ValueError("Unable to generate valid SQL.")



def normalize_result_alias(sql: str, question: str) -> str:
    q = question.lower()

    alias_rules = [
        ("customer", "customer_count"),
        ("employee", "employee_count"),
        ("product", "product_count"),
    ]

    if re.search(r"\bcount\s*\(", sql, re.I):
        for keyword, alias in alias_rules:
            if keyword in q:
                if not re.search(r"\bAS\s+" + alias + r"\b", sql, re.I):
                    sql = re.sub(
                        r"\bCOUNT\s*\(\s*\*\s*\)",
                        f"COUNT(*) AS {alias}",
                        sql,
                        count=1,
                        flags=re.I,
                    )
                break

    if "delivered" in q and "revenue" in q:
        if re.search(r"\bSUM\s*\(\s*s\.revenue\s*\)", sql, re.I):
            if not re.search(r"\bAS\s+total_delivered_revenue\b", sql, re.I):
                sql = re.sub(
                    r"\bSUM\s*\(\s*s\.revenue\s*\)",
                    "SUM(s.revenue) AS total_delivered_revenue",
                    sql,
                    count=1,
                    flags=re.I,
                )

    
    if "revenue" in q and re.search(r"\bSUM\s*\(\s*revenue\s*\)", sql, re.I):
        sql = re.sub(
            r"\bSUM\s*\(\s*revenue\s*\)(?:\s+AS\s+[a-z_][a-z0-9_]*)?",
            "SUM(revenue) AS total_revenue",
            sql,
            count=1,
            flags=re.I,
        )
       

    return sql



def ask_sql(question: str):
    client = Groq(api_key=GROQ_API_KEY)

    sql = generate_sql(question)
    sql = normalize_result_alias(sql, question)
    sql = validate_sql(sql)

    for attempt in range(2):
        try:
            rows = select_rows(sql)

            return {
                "sql": sql,
                "rows": rows,
            }

        except Exception as error:
            if attempt == 1:
                raise

            correction_prompt = f"""
The following PostgreSQL SELECT query failed.

SQL:
{sql}

Database error:
{str(error)}

Original question:
{question}

Generate one corrected PostgreSQL SELECT query.
Use only the supplied schema:
{SCHEMA}

Rules:
- Use only SELECT.
- Do not invent columns.
- Correct all GROUP BY and aggregate errors.
- For monthly revenue, group by the month expression.
- Do not filter order status unless explicitly requested.
- Return SQL only.
"""

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Return only valid PostgreSQL SELECT SQL."
                    },
                    {
                        "role": "user",
                        "content": correction_prompt
                    }
                ],
                temperature=0,
            )

            sql = response.choices[0].message.content or ""
            sql = validate_sql(sql)
            sql = normalize_result_alias(sql, question)
            sql = validate_sql(sql)

    raise RuntimeError("SQL execution failed.")

