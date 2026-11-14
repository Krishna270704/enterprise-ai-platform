def route_query(q):
    s = q.lower()

    doc = any(x in s for x in [
        "policy", "document", "according to",
        "refund", "return", "leave", "hr",
        "contract", "report", "file"
    ])

    analytics = any(x in s for x in [
        "trend", "forecast", "anomal",
        "growth", "compare", "monthly",
        "over time", "root cause", "visual",
        "performance", "increase", "decrease",
        "analyze", "analysis"
    ])

    sql = any(x in s for x in [
        "how many", "total", "average",
        "revenue", "customers", "employees",
        "inventory", "stock", "orders",
        "products", "count", "database", "records"
    ])

    # Combined routing
    if doc and sql and analytics:
        return "full_hybrid"

    if doc and sql:
        return "hybrid"

    if doc and analytics:
        return "document_analytics"

    if sql and analytics:
        return "sql_analytics"

    if analytics:
        return "analytics"

    if sql:
        return "sql"

    return "documents"