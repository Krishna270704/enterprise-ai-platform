import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import main


def test_full_hybrid_executes_all_modules(monkeypatch):
    monkeypatch.setattr(
        main,
        "retrieve",
        lambda question, k, source_filter=None: [{
            "source": "HR_Policy.txt",
            "text": "Casual leave requires manager approval.",
            "score": 1.0,
        }],
    )
    monkeypatch.setattr(
        main,
        "ask_sql",
        lambda question: {
            "sql": "SELECT COUNT(*) AS customer_count FROM customers",
            "rows": [{"customer_count": 30}],
        },
    )
    monkeypatch.setattr(
        main,
        "run_analytics",
        lambda question: {
            "monthly_trend": [{"month": "2026-01", "revenue": 100.0}],
            "monthly_extrema": None,
        },
    )
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda question, evidence, analytics_result=None: "Grounded answer.",
    )

    response = TestClient(main.app).post(
        "/api/query",
        json={
            "question": (
                "According to the HR policy, how many customers are there "
                "and what is the monthly sales trend?"
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "full_hybrid"
    assert {item["type"] for item in payload["evidence"]} == {
        "document",
        "database",
        "analytics",
    }
    assert payload["module_errors"] == []
