
def precision_at_k(retrieved, relevant, k=5):
    if k <= 0:
        raise ValueError("k must be greater than zero")

    results = retrieved[:k]

    relevant_count = sum(
        1 for item in results
        if item.get("source") in relevant
    )

    return relevant_count / k


def recall_at_k(retrieved, relevant, k=5):
    if not relevant:
        return 0.0

    results = retrieved[:k]

    relevant_count = sum(
        1 for item in results
        if item.get("source") in relevant
    )

    return relevant_count / len(relevant)


def reciprocal_rank(retrieved, relevant):
    for rank, item in enumerate(retrieved, start=1):
        if item.get("source") in relevant:
            return 1.0 / rank

    return 0.0


def evaluate_retrieval(test_cases, k=5):
    results = []

    for case in test_cases:
        retrieved = case["retrieved"]
        relevant = set(case["relevant"])

        results.append({
            "query": case["query"],
            "precision_at_k": round(
                precision_at_k(retrieved, relevant, k), 4
            ),
            "recall_at_k": round(
                recall_at_k(retrieved, relevant, k), 4
            ),
            "reciprocal_rank": round(
                reciprocal_rank(retrieved, relevant), 4
            )
        })

    if not results:
        return {
            "cases": [],
            "mean_precision_at_k": 0.0,
            "mean_recall_at_k": 0.0,
            "mrr": 0.0
        }

    count = len(results)

    return {
        "cases": results,
        "mean_precision_at_k": round(
            sum(x["precision_at_k"] for x in results) / count, 4
        ),
        "mean_recall_at_k": round(
            sum(x["recall_at_k"] for x in results) / count, 4
        ),
        "mrr": round(
            sum(x["reciprocal_rank"] for x in results) / count, 4
        )
    }
