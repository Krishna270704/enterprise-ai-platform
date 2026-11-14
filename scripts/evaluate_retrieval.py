
import sys
import json
import csv
import time

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ingestion import retrieve
from app.evaluation import evaluate_retrieval


TEST_CASES = [
    {
        "query": "What is the refund and return policy?",
        "relevant": ["Refund_Return_Policy.txt"]
    },
    {
        "query": "What is the company employee leave policy?",
        "relevant": ["HR_Policy.txt"]
    },
    {
        "query": "What happens when inventory stock reaches reorder level?",
        "relevant": ["Inventory_Policy.txt"]
    },
    {
        "query": "What products are available in the product catalogue?",
        "relevant": ["Product_Catalogue.txt"]
    },
    {
    "query": "What are the company's financial performance details?",
    "relevant": ["Financial_Report.txt"]
    }
]


def main():
    evaluated_cases = []
    timings = []

    print("\nENTERPRISE AI RETRIEVAL BENCHMARK")
    print("=" * 50)

    for index, case in enumerate(TEST_CASES, start=1):
        print(f"\nTest {index}: {case['query']}")

        start = time.perf_counter()

        retrieved = retrieve(
            case["query"],
            k=5
        )

        latency = time.perf_counter() - start
        timings.append(latency)

        print("Relevant documents:", case["relevant"])
        print("Retrieved documents:")

        for rank, item in enumerate(retrieved, start=1):
            print(
                f"{rank}. {item['source']} "
                f"(score={item['score']})"
            )

        evaluated_cases.append({
            "query": case["query"],
            "relevant": case["relevant"],
            "retrieved": retrieved
        })

    metrics = evaluate_retrieval(
        evaluated_cases,
        k=5
    )

    summary = {
        "benchmark": "TechNova synthetic document retrieval",
        "number_of_queries": len(TEST_CASES),
        "k": 5,
        "mean_precision_at_5": metrics["mean_precision_at_k"],
        "mean_recall_at_5": metrics["mean_recall_at_k"],
        "mrr": metrics["mrr"],
        "average_latency_seconds": round(
            sum(timings) / len(timings), 3
        ),
        "results": metrics["cases"]
    }

    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "retrieval_evaluation.json"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    csv_path = output_dir / "retrieval_evaluation.csv"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "query",
                "precision_at_k",
                "recall_at_k",
                "reciprocal_rank"
            ]
        )
        writer.writeheader()
        writer.writerows(metrics["cases"])

    print("\n" + "=" * 50)
    print("BENCHMARK SUMMARY")
    print("=" * 50)
    print(json.dumps(summary, indent=4))

    print("\nSaved results:")
    print(json_path)
    print(csv_path)


if __name__ == "__main__":
    main()
