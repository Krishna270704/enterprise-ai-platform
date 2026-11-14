import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation import precision_at_k


def test_precision_at_k_uses_requested_k_as_denominator():
    assert precision_at_k(
        [{"source": "HR_Policy.txt"}],
        {"HR_Policy.txt"},
        k=5,
    ) == 0.2
