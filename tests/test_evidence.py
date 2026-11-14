
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evidence import fuse_evidence, verify_answer


def test_empty_evidence():
    result = verify_answer("There are 30 customers.", [])

    assert result["status"] == "insufficient_evidence"
    assert result["support_ratio"] == 0.0


def test_supported_numeric_answer():
    evidence = [
        {
            "type": "database",
            "source": "PostgreSQL",
            "content": {
                "sql": "SELECT COUNT(*) FROM customers",
                "rows": [{"customer_count": 30}]
            }
        }
    ]

    result = verify_answer(
        "There are 30 customers.",
        evidence
    )

    assert result["status"] == "supported"
    assert result["support_ratio"] == 1.0


def test_unsupported_numeric_answer():
    evidence = [
        {
            "type": "database",
            "source": "PostgreSQL",
            "content": {
                "rows": [{"customer_count": 30}]
            }
        }
    ]

    result = verify_answer(
        "There are 100 customers.",
        evidence
    )

    assert result["status"] == "review_required"
    assert result["support_ratio"] == 0.0


def test_document_evidence():
    evidence = fuse_evidence(
        document_hits=[
            {
                "source": "Refund_Return_Policy.txt",
                "text": "Refunds are processed within 7 business days.",
                "score": 0.8
            }
        ]
    )

    result = verify_answer(
        "Refunds are processed within 7 business days.",
        evidence
    )

    assert len(evidence) == 1
    assert result["support_ratio"] > 0


def test_duplicate_document_evidence():
    document = {
        "source": "HR_Policy.txt",
        "text": "Employees receive annual leave.",
        "score": 0.8
    }

    evidence = fuse_evidence(
        document_hits=[document, document]
    )

    assert len(evidence) == 1


def test_database_evidence_fusion():
    evidence = fuse_evidence(
        sql_result={
            "sql": "SELECT COUNT(*) FROM customers",
            "rows": [{"count": 30}]
        }
    )

    assert len(evidence) == 1
    assert evidence[0]["type"] == "database"
