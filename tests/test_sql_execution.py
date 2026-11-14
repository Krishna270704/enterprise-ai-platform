
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.sql_agent import ask_sql


TEST_CASES = [
    {
        "question": "How many customers are there?",
        "column": "customer_count",
        "expected": 30
    },
    {
        "question": "How many employees are there?",
        "column": "employee_count",
        "expected": 15
    },
    {
        "question": "How many products are there?",
        "column": "product_count",
        "expected": 6
    },
    {
        "question": "Calculate total revenue from delivered orders only",
        "column": "total_delivered_revenue",
        "expected": 5353600
    }
]


def test_sql_execution_accuracy():
    passed = 0

    for case in TEST_CASES:
        result = ask_sql(case["question"])

        assert result["rows"], (
            f"No rows returned for: {case['question']}"
        )

        actual = result["rows"][0][case["column"]]

        assert float(actual) == float(case["expected"]), (
            f"Incorrect result for {case['question']}: "
            f"expected {case['expected']}, got {actual}"
        )

        passed += 1

    assert passed == len(TEST_CASES)
