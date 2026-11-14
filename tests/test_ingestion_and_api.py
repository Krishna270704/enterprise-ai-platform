import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import ingestion, main
from app.evidence import verify_answer
from app.llm import focus_document_evidence


class FakeCollection:
    def count(self):
        return 2

    def get(self, include=None):
        return {
            "documents": ["Casual leave requires approval.", "Unrelated policy."],
            "metadatas": [
                {"source": "hr.txt", "chunk": 0},
                {"source": "other.txt", "chunk": 0},
            ],
        }

    def query(self, query_embeddings, n_results, where=None):
        return {
            "documents": [["Casual leave requires approval.", "Unrelated policy."]],
            "metadatas": [[
                {"source": "hr.txt", "chunk": 0},
                {"source": "other.txt", "chunk": 0},
            ]],
            "distances": [[0.1, 1.0]],
        }


class FakeEmbeddingModel:
    class Encoded:
        def __init__(self, values):
            self.values = values

        def tolist(self):
            return self.values

    def encode(self, values, normalize_embeddings=True):
        return self.Encoded([[1.0, 0.0] for _ in values])


class FakeReranker:
    def predict(self, pairs):
        return [1.0 for _ in pairs]


def test_retrieve_rejects_semantically_weak_nonmatching_documents(monkeypatch):
    monkeypatch.setattr(ingestion, "get_collection", lambda: FakeCollection())
    monkeypatch.setattr(
        ingestion,
        "get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )
    monkeypatch.setattr(ingestion, "get_reranker", lambda: FakeReranker())

    results = ingestion.retrieve("What is the casual leave process?", k=5)

    assert [item["source"] for item in results] == ["hr.txt"]


def test_document_verifier_rejects_unsupported_numeric_claim():
    result = verify_answer(
        "Casual leave takes 9 days.",
        [{
            "type": "document",
            "content": "Casual leave requires manager approval within two business days.",
        }],
    )

    assert result["status"] == "review_required"
    assert result["support_ratio"] == 0.0


def test_empty_upload_returns_bad_request(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    client = TestClient(main.app)

    response = client.post(
        "/api/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded document is empty."


def test_document_focus_excludes_unrelated_policy_sentence():
    focused = focus_document_evidence(
        "What is the process for taking casual leave?",
        [{
            "type": "document",
            "source": "HR_Policy.txt",
            "content": (
                "Casual leave requires manager approval. "
                "HR requests are submitted through the employee portal. "
                "Payroll is processed on the final working day of each month."
            ),
        }],
    )

    assert "manager approval" in focused[0]["content"]
    assert "employee portal" in focused[0]["content"]
    assert "Payroll" not in focused[0]["content"]
