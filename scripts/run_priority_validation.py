"""Run the controlled research validation requested for the project.

The script uses the existing PostgreSQL and ChromaDB data read-only. Groq is
required for the natural-language SQL cases and the live API route checks.
Temporary ingestion fixtures are indexed with deterministic IDs and removed
from ChromaDB before the script exits.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.analytics import run_analytics as calculate_analytics
from app.db import select_rows
from app.evaluation import evaluate_retrieval
from app.evidence import fuse_evidence, verify_answer
from app.ingestion import extract_text, get_collection, index_document, retrieve
from app.sql_agent import ask_sql, validate_sql

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


RAG_CASES = [
    ("RAG-01", "What is the return window?", ["Refund_Return_Policy.txt"]),
    ("RAG-02", "When are refunds processed?", ["Refund_Return_Policy.txt"]),
    ("RAG-03", "What is the casual leave policy?", ["HR_Policy.txt"]),
    ("RAG-04", "Where are HR requests submitted?", ["HR_Policy.txt"]),
    ("RAG-05", "What happens at the inventory reorder level?", ["Inventory_Policy.txt"]),
    ("RAG-06", "How often is inventory reviewed?", ["Inventory_Policy.txt"]),
    ("RAG-07", "What products are in the catalogue?", ["Product_Catalogue.txt"]),
    ("RAG-08", "What is the NovaBook Pro price?", ["Product_Catalogue.txt"]),
    ("RAG-09", "How is revenue calculated?", ["Financial_Report.txt"]),
    ("RAG-10", "Is the financial note an actual company statement?", ["Financial_Report.txt"]),
]


SQL_CASES = [
    ("SQL-01", "How many customers are there?", "SELECT COUNT(*) FROM customers"),
    ("SQL-02", "How many employees are there?", "SELECT COUNT(*) FROM employees"),
    ("SQL-03", "How many products are there?", "SELECT COUNT(*) FROM products"),
    ("SQL-04", "How many orders are there?", "SELECT COUNT(*) FROM orders"),
    ("SQL-05", "How many delivered orders are there?", "SELECT COUNT(*) FROM orders WHERE status = 'Delivered'"),
    ("SQL-06", "What is the total revenue?", "SELECT SUM(revenue) FROM sales"),
    ("SQL-07", "Show monthly revenue.", "SELECT to_char(sale_date, 'YYYY-MM'), SUM(revenue) FROM sales GROUP BY 1 ORDER BY 1"),
    ("SQL-08", "Show revenue by city.", "SELECT city, SUM(revenue) FROM sales GROUP BY city ORDER BY city"),
    ("SQL-09", "Show product-wise sales revenue.", "SELECT p.name, SUM(s.revenue) FROM sales s JOIN products p ON p.product_id=s.product_id GROUP BY p.name ORDER BY p.name"),
    ("SQL-10", "Which inventory items are below reorder level?", "SELECT product_id, stock, reorder_level FROM inventory WHERE stock < reorder_level ORDER BY product_id"),
]


ROUTE_CASES = [
    ("documents", "What is the HR policy?"),
    ("sql", "How many customers are there?"),
    ("analytics", "Show monthly sales trend"),
    ("hybrid", "What is the refund policy and how many customers are there?"),
    ("document_analytics", "What is the leave policy and show monthly trend?"),
    ("sql_analytics", "What is total revenue trend?"),
    ("full_hybrid", "According to the HR policy, how many customers are there and what is the monthly sales trend?"),
]

EXPECTED_DOCUMENT_SOURCES = {
    "HR_Policy.txt",
    "Refund_Return_Policy.txt",
    "Inventory_Policy.txt",
    "Product_Catalogue.txt",
    "Financial_Report.txt",
}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def scalar(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), 8)
    try:
        return round(float(value), 8)
    except (TypeError, ValueError):
        return str(value)


def canonical_rows(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return sorted(
        tuple(sorted((key, scalar(value)) for key, value in row.items()))
        for row in rows
    )


def precision_over_returned(retrieved, relevant) -> float:
    if not retrieved:
        return 0.0
    return sum(
        item.get("source") in relevant
        for item in retrieved
    ) / len(retrieved)


def chroma_source_counts() -> Counter:
    stored = get_collection().get(include=["metadatas"])
    return Counter(
        metadata.get("source")
        for metadata in stored.get("metadatas") or []
        if metadata.get("source")
    )


def compare_sql_results(query_id: str, actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> bool:
    if query_id in {"SQL-01", "SQL-02", "SQL-03", "SQL-04", "SQL-05", "SQL-06"}:
        actual_value = next(iter(actual[0].values()), None) if actual else None
        expected_value = next(iter(expected[0].values()), None) if expected else None
        return scalar(actual_value) == scalar(expected_value)
    if query_id == "SQL-07":
        def monthly(rows):
            return sorted(
                (str(next(iter(row.values()))).split(" ")[0][:7], scalar(list(row.values())[-1]))
                for row in rows
            )
        return monthly(actual) == monthly(expected)
    if query_id == "SQL-08":
        return sorted(
            (row.get("city"), scalar(next(value for key, value in row.items() if key != "city")))
            for row in actual
        ) == sorted(
            (row.get("city"), scalar(next(value for key, value in row.items() if key != "city")))
            for row in expected
        )
    if query_id == "SQL-09":
        def products(rows):
            return sorted(
                (row.get("name"), scalar(next(value for key, value in row.items() if key in {"sum", "total_revenue"})))
                for row in rows
            )
        return products(actual) == products(expected)
    if query_id == "SQL-10":
        fields = ("product_id", "stock", "reorder_level")
        return sorted(tuple(scalar(row.get(field)) for field in fields) for row in actual) == sorted(
            tuple(scalar(row.get(field)) for field in fields) for row in expected
        )
    return canonical_rows(actual) == canonical_rows(expected)


def run_rag(root: Path) -> dict[str, Any]:
    cases = []
    for query_id, question, relevant in RAG_CASES:
        started = time.perf_counter()
        retrieved = retrieve(question, k=5)
        metrics = evaluate_retrieval(
            [{"query": question, "relevant": relevant, "retrieved": retrieved}],
            k=5,
        )["cases"][0]
        returned_count = len(retrieved)
        returned_precision = precision_over_returned(retrieved, set(relevant))
        recall_pass = metrics["recall_at_k"] == 1
        no_irrelevant_results = returned_precision == 1
        cases.append({
            "query_id": query_id,
            "question": question,
            "expected_relevant_source": "|".join(relevant),
            "retrieved_sources": "|".join(item["source"] for item in retrieved),
            "retrieved_document_count": returned_count,
            "precision_at_5": metrics["precision_at_k"],
            "precision_over_returned": round(returned_precision, 4),
            "recall_at_5": metrics["recall_at_k"],
            "reciprocal_rank": metrics["reciprocal_rank"],
            "result": (
                "PASS"
                if recall_pass and no_irrelevant_results
                else "REVIEW_REQUIRED"
            ),
            "latency_seconds": round(time.perf_counter() - started, 4),
        })
    path = root / "RAG_EVALUATION_RESULTS.csv"
    write_csv(path, cases, list(cases[0]))
    return {
        "cases": cases,
        "precision_at_5": round(sum(row["precision_at_5"] for row in cases) / len(cases), 4),
        "precision_over_returned": round(
            sum(row["precision_over_returned"] for row in cases) / len(cases),
            4,
        ),
        "recall_at_5": round(sum(row["recall_at_5"] for row in cases) / len(cases), 4),
        "mrr": round(sum(row["reciprocal_rank"] for row in cases) / len(cases), 4),
        "path": str(path),
    }


def run_sql(root: Path) -> dict[str, Any]:
    rows = []
    for query_id, question, expected_sql in SQL_CASES:
        started = time.perf_counter()
        try:
            generated = ask_sql(question)
            actual_rows = generated["rows"]
            expected_rows = select_rows(expected_sql)
            passed = compare_sql_results(query_id, actual_rows, expected_rows)
            rows.append({
                "query_id": query_id,
                "natural_language_question": question,
                "generated_sql": generated["sql"],
                "expected_result": json.dumps(expected_rows, default=str),
                "actual_result": json.dumps(actual_rows, default=str),
                "correctness": "PASS" if passed else "FAIL",
                "execution_status": "success",
                "latency_seconds": round(time.perf_counter() - started, 4),
            })
        except Exception as error:
            rows.append({
                "query_id": query_id,
                "natural_language_question": question,
                "generated_sql": "",
                "expected_result": json.dumps(select_rows(expected_sql), default=str),
                "actual_result": "",
                "correctness": "BLOCKED" if "429" in str(error) else "FAIL",
                "execution_status": "blocked_by_provider_rate_limit" if "429" in str(error) else "failure",
                "latency_seconds": round(time.perf_counter() - started, 4),
            })
    path = root / "SQL_EVALUATION_RESULTS.csv"
    write_csv(path, rows, list(rows[0]))
    safety_inputs = [
        "INSERT INTO customers VALUES ('x')",
        "UPDATE customers SET name='x'",
        "DELETE FROM customers",
        "DROP TABLE customers",
        "SELECT * FROM customers; SELECT * FROM employees",
        "SELECT * FROM unknown_table",
        "SELECT * FROM customers -- comment",
        "SELECT pg_sleep(1) FROM customers",
    ]
    safety_passed = 0
    for statement in safety_inputs:
        try:
            validate_sql(statement)
        except ValueError:
            safety_passed += 1
    return {
        "cases": rows,
        "accuracy": round(sum(row["correctness"] == "PASS" for row in rows) / len(rows), 4),
        "safety_cases": len(safety_inputs),
        "safety_passed": safety_passed,
        "path": str(path),
    }


def run_analytics(root: Path) -> dict[str, Any]:
    actual = calculate_analytics("Show monthly sales trend")
    expected_monthly = {
        row["month"]: float(row["revenue"])
        for row in select_rows(
            "SELECT to_char(sale_date, 'YYYY-MM') AS month, SUM(revenue) AS revenue FROM sales GROUP BY 1 ORDER BY 1"
        )
    }
    expected_city = {
        row["city"]: float(row["revenue"])
        for row in select_rows(
            "SELECT city, SUM(revenue) AS revenue FROM sales GROUP BY city ORDER BY city"
        )
    }
    expected_product = {
        row["product_name"]: float(row["revenue"])
        for row in select_rows(
            "SELECT p.name AS product_name, SUM(s.revenue) AS revenue FROM sales s JOIN products p ON p.product_id=s.product_id GROUP BY p.name ORDER BY p.name"
        )
    }
    sales_rows = select_rows("SELECT sale_date, city, revenue FROM sales")
    frame = pd.DataFrame(sales_rows)
    frame["revenue"] = pd.to_numeric(frame["revenue"])
    mean = float(frame["revenue"].mean())
    std = float(frame["revenue"].std())
    expected_anomalies = {
        (str(row["sale_date"]), row["city"], float(row["revenue"]))
        for row in sales_rows
        if abs(float(row["revenue"]) - mean) > 2 * std
    }
    actual_anomalies = {
        (row["sale_date"], row["city"], float(row["revenue"]))
        for row in actual["anomalies"]
    }
    metrics = [
        ("monthly_revenue", expected_monthly, {row["month"]: float(row["revenue"]) for row in actual["monthly_trend"]}),
        ("maximum_month", max(expected_monthly.items(), key=lambda item: item[1]), max({row["month"]: float(row["revenue"]) for row in actual["monthly_trend"]}.items(), key=lambda item: item[1])),
        ("minimum_month", min(expected_monthly.items(), key=lambda item: item[1]), min({row["month"]: float(row["revenue"]) for row in actual["monthly_trend"]}.items(), key=lambda item: item[1])),
        ("city_revenue", expected_city, actual["revenue_by_city"]),
        ("product_revenue", expected_product, actual["revenue_by_product"]),
        ("anomaly_indicators", expected_anomalies, actual_anomalies),
    ]
    validation_rows = []
    for metric, expected, observed in metrics:
        equal = expected == observed
        validation_rows.append({
            "metric": metric,
            "expected_sql_result": json.dumps(expected, default=str),
            "actual_application_result": json.dumps(observed, default=str),
            "difference": "0" if equal else "mismatch",
            "validation_status": "PASS" if equal else "FAIL",
        })
    forecast = actual["forecast"]
    validation_rows.append({
        "metric": "forecast_output",
        "expected_sql_result": "No labelled future target available",
        "actual_application_result": json.dumps(forecast, default=str),
        "difference": "not measurable",
        "validation_status": "EXPERIMENTAL_UNVALIDATED",
    })
    path = root / "ANALYTICS_VALIDATION_RESULTS.csv"
    write_csv(path, validation_rows, list(validation_rows[0]))
    return {
        "rows": validation_rows,
        "passed": sum(row["validation_status"] == "PASS" for row in validation_rows),
        "failed": sum(row["validation_status"] == "FAIL" for row in validation_rows),
        "forecast": forecast,
        "path": str(path),
    }


def run_ingestion_checks(run_id: str) -> dict[str, Any]:
    from docx import Document
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    checks = []
    temporary_sources = []
    try:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            files = {
                f"__priority_validation_{run_id}.txt": "Temporary TXT leave policy.",
                f"__priority_validation_{run_id}.md": "# Temporary Markdown policy.",
                f"__priority_validation_{run_id}.csv": "key,value\nleave,approval\n",
            }
            for name, content in files.items():
                path = folder / name
                path.write_text(content, encoding="utf-8")
                temporary_sources.append(name)
                result = index_document(path)
                checks.append({"format": path.suffix, "extracted_text": extract_text(path), "chunks": result["chunks"]})
            docx_path = folder / f"__priority_validation_{run_id}.docx"
            temporary_sources.append(docx_path.name)
            document = Document()
            document.add_paragraph("Temporary DOCX policy.")
            document.save(docx_path)
            result = index_document(docx_path)
            checks.append({"format": ".docx", "extracted_text": extract_text(docx_path), "chunks": result["chunks"]})
            pdf_path = folder / f"__priority_validation_{run_id}.pdf"
            temporary_sources.append(pdf_path.name)
            writer = PdfWriter()
            page = writer.add_blank_page(width=300, height=300)
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 20 100 Td (Temporary PDF policy.) Tj ET")
            page[NameObject("/Contents")] = writer._add_object(stream)
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            resources = DictionaryObject({
                NameObject("/Font"): DictionaryObject({
                    NameObject("/F1"): writer._add_object(font),
                }),
            })
            page[NameObject("/Resources")] = resources
            with pdf_path.open("wb") as handle:
                writer.write(handle)
            pdf_text = extract_text(pdf_path)
            result = index_document(pdf_path)
            checks.append({"format": ".pdf", "extracted_text": pdf_text, "chunks": result["chunks"]})
    finally:
        collection = get_collection()
        ids = collection.get(
            where={"source": {"$in": temporary_sources}}
        )["ids"]
        if ids:
            collection.delete(ids=ids)
    return {
        "checks": checks,
        "all_extraction_paths_exercised": len(checks) == 5,
        "temporary_sources": temporary_sources,
    }


def run_verifier_checks() -> list[dict[str, Any]]:
    cases = [
        ("supported_claim", "Casual leave requires manager approval.", "Casual leave requires manager approval.", "supported"),
        ("unsupported_claim", "Payroll determines leave approval.", "Casual leave requires manager approval.", "review_required"),
        ("unsupported_number", "Casual leave takes 9 days.", "Casual leave requires manager approval within two business days.", "review_required"),
        ("missing_evidence", "There are 30 customers.", "", "insufficient_evidence"),
    ]
    results = []
    for name, answer, content, expected in cases:
        evidence = [{"type": "document", "source": "HR_Policy.txt", "content": content}] if content else []
        actual = verify_answer(answer, evidence)
        results.append({"case": name, "expected": expected, "actual": actual["status"], "pass": actual["status"] == expected})
    return results


def run_route_checks() -> list[dict[str, Any]]:
    required_types = {
        "documents": {"document"},
        "sql": {"database"},
        "analytics": {"analytics"},
        "hybrid": {"document", "database"},
        "document_analytics": {"document", "analytics"},
        "sql_analytics": {"database", "analytics"},
        "full_hybrid": {"document", "database", "analytics"},
    }
    results = []
    with httpx.Client(base_url=API_URL, timeout=180) as client:
        for expected, question in ROUTE_CASES:
            try:
                response = client.post("/api/query", json={"question": question})
                payload = response.json()
                types = {item.get("type") for item in payload.get("evidence", [])}
                passed = (
                    response.status_code == 200
                    and payload.get("route") == expected
                    and required_types[expected].issubset(types)
                    and not payload.get("module_errors")
                )
                results.append({
                    "expected_route": expected,
                    "actual_route": payload.get("route"),
                    "question": question,
                    "executed_evidence_types": "|".join(sorted(types)),
                    "module_errors": json.dumps(payload.get("module_errors", [])),
                    "pass": passed,
                })
            except Exception as error:
                results.append({
                    "expected_route": expected,
                    "actual_route": "",
                    "question": question,
                    "executed_evidence_types": "",
                    "module_errors": str(error),
                    "pass": False,
                })
    return results


def run_casual_leave_check() -> dict[str, Any]:
    question = "What is the process for taking casual leave?"
    try:
        with httpx.Client(base_url=API_URL, timeout=180) as client:
            response = client.post("/api/query", json={"question": question})
        payload = response.json()
        answer = str(payload.get("answer", ""))
        lower = answer.lower()
        unsupported_payroll_link = bool(
            ("leave" in lower or "casual" in lower)
            and "payroll" in lower
            and ("reflect" in lower or "processed" in lower)
        )
        return {
            "question": question,
            "http_status": response.status_code,
            "sources": "|".join(item.get("source", "") for item in payload.get("evidence", [])),
            "verification_status": (payload.get("verification") or {}).get("status"),
            "unsupported_payroll_link_detected": unsupported_payroll_link,
            "answer": answer,
            "pass": response.status_code == 200 and not unsupported_payroll_link,
        }
    except Exception as error:
        return {
            "question": question,
            "http_status": "",
            "sources": "",
            "verification_status": "",
            "unsupported_payroll_link_detected": False,
            "answer": "",
            "pass": False,
            "error": str(error),
        }


def main() -> None:
    root = ROOT
    run_id = uuid.uuid4().hex
    chroma_before = chroma_source_counts()
    ingestion = run_ingestion_checks(run_id)
    chroma_after = chroma_source_counts()
    ingestion["chroma_existing_sources_intact"] = all(
        chroma_after[source] == chroma_before[source]
        for source in EXPECTED_DOCUMENT_SOURCES
    )
    ingestion["chroma_record_count_before"] = sum(chroma_before.values())
    ingestion["chroma_record_count_after"] = sum(chroma_after.values())
    rag = run_rag(root)
    sql = run_sql(root)
    analytics = run_analytics(root)
    verification = run_verifier_checks()
    route_rows = run_route_checks()
    casual_leave = run_casual_leave_check()
    payload = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": "Synthetic TechNova documents and enterprise_ai_demo PostgreSQL records",
        "rag": rag,
        "sql": sql,
        "analytics": analytics,
        "ingestion": ingestion,
        "verification": verification,
        "routes": route_rows,
        "casual_leave": casual_leave,
    }
    (root / "priority_validation_raw.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "rag_precision_at_5": rag["precision_at_5"],
        "rag_recall_at_5": rag["recall_at_5"],
        "rag_mrr": rag["mrr"],
        "sql_accuracy": sql["accuracy"],
        "sql_safety": f'{sql["safety_passed"]}/{sql["safety_cases"]}',
        "analytics_passed": analytics["passed"],
        "analytics_failed": analytics["failed"],
        "verification_passed": sum(item["pass"] for item in verification),
        "route_passed": sum(item["pass"] for item in route_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
