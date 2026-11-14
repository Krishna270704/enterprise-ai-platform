import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.analytics import run_analytics
from app import llm
from app.llm import monthly_extrema_are_supported


ANALYTICS = {
    "monthly_extrema": {
        "maximum": {"month": "2026-05", "revenue": 1569800.0},
        "minimum": {"month": "2026-04", "revenue": 546000.0},
    }
}


def test_monthly_extrema_accepts_computed_months():
    answer = (
        "Revenue peaks in May 2026 at 1,569,800 and reaches its "
        "lowest point in April 2026 at 546,000."
    )

    assert monthly_extrema_are_supported(answer, ANALYTICS)


def test_monthly_extrema_rejects_incorrect_minimum_interpretation():
    answer = (
        "Revenue peaks in May 2026 at 1,569,800 and reaches a trough "
        "in October 2026 at 583,200."
    )

    assert not monthly_extrema_are_supported(answer, ANALYTICS)


def test_monthly_extrema_rejects_incorrect_maximum_interpretation():
    answer = (
        "Revenue reaches a high in June 2026 at 1,253,400 and a low "
        "in April 2026 at 546,000."
    )

    assert not monthly_extrema_are_supported(answer, ANALYTICS)


def test_analytics_calculates_extrema_from_monthly_rows(monkeypatch):
    rows = [
        {
            "sale_date": "2026-01-15",
            "city": "Delhi",
            "revenue": 100,
            "quantity": 1,
            "product_id": "P1",
            "product_name": "Product",
            "category": "Category",
        },
        {
            "sale_date": "2026-02-15",
            "city": "Delhi",
            "revenue": 300,
            "quantity": 1,
            "product_id": "P1",
            "product_name": "Product",
            "category": "Category",
        },
        {
            "sale_date": "2026-03-15",
            "city": "Delhi",
            "revenue": 200,
            "quantity": 1,
            "product_id": "P1",
            "product_name": "Product",
            "category": "Category",
        },
    ]
    monkeypatch.setattr("app.analytics.select_rows", lambda query: rows)

    result = run_analytics("Show monthly sales trend")

    assert result["monthly_extrema"] == {
        "maximum": {"month": "2026-02", "revenue": 300.0},
        "minimum": {"month": "2026-01", "revenue": 100.0},
    }


def test_generated_incorrect_extrema_are_replaced_with_verified_facts(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {
                                "message": type(
                                    "Message",
                                    (),
                                    {
                                        "content": (
                                            "The peak was June 2026 at 1,253,400 "
                                            "and the trough was October 2026 at 583,200."
                                        )
                                    },
                                )()
                            },
                        )()
                    ]
                },
            )()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(llm, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm, "Groq", lambda api_key: FakeClient())

    answer = llm.generate_answer(
        "Show monthly sales trend",
        [{"type": "analytics", "source": "TechNova sales tables"}],
        analytics_result=ANALYTICS,
    )

    assert "2026-05" in answer
    assert "2026-04" in answer
    assert "October 2026" not in answer
