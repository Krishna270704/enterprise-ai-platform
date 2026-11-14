import numpy as np
import pandas as pd
from .db import select_rows


def run_analytics(question):
    rows = select_rows("""
        SELECT
            s.sale_date,
            s.city,
            s.revenue,
            s.quantity,
            s.product_id,
            p.name AS product_name,
            p.category
        FROM sales s
        LEFT JOIN products p ON s.product_id = p.product_id
        ORDER BY s.sale_date
    """)

    if not rows:
        return {"message": "No sales data. Load demo data first."}

    df = pd.DataFrame(rows)

    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df = df.dropna(subset=["revenue", "sale_date"])

    # 1. Overall revenue
    total_revenue = float(df["revenue"].sum())

    # 2. Monthly revenue trend
    monthly = (
        df.groupby(df["sale_date"].dt.to_period("M"))["revenue"]
        .sum()
        .reset_index()
    )
    monthly["month"] = monthly["sale_date"].astype(str)
    monthly = monthly.drop(columns=["sale_date"])
    monthly["revenue"] = monthly["revenue"].astype(float)

    maximum_month = monthly.loc[monthly["revenue"].idxmax()]
    minimum_month = monthly.loc[monthly["revenue"].idxmin()]
    monthly_extrema = {
        "maximum": {
            "month": str(maximum_month["month"]),
            "revenue": float(maximum_month["revenue"]),
        },
        "minimum": {
            "month": str(minimum_month["month"]),
            "revenue": float(minimum_month["revenue"]),
        },
    }

    # 3. City-wise revenue
    city_revenue = (
        df.groupby("city")["revenue"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    # 4. Anomaly detection: basic 2-standard-deviation heuristic
    mean = float(df["revenue"].mean())
    std = float(df["revenue"].std())

    if pd.isna(std) or std == 0:
        anomalies = []
    else:
        anomalies = (
            df[(df["revenue"] - mean).abs() > 2 * std]
            [["sale_date", "city", "revenue"]]
            .astype(str)
            .to_dict("records")
        )

    # 5. Revenue forecasting using linear regression
    forecast = {
        "status": "not_available",
        "next_month": None,
        "predicted_revenue": None,
        "method": "Linear trend"
    }

    if len(monthly) >= 3:
        values = monthly["revenue"].astype(float).to_numpy()
        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)

        prediction = max(0.0, float(slope * len(values) + intercept))

        last_month = pd.Period(monthly["month"].iloc[-1], freq="M")
        next_month = str(last_month + 1)

        forecast = {
            "status": "available",
            "next_month": next_month,
            "predicted_revenue": round(prediction, 2),
            "method": "Linear regression on monthly revenue",
            "note": "Experimental estimate, not a validated business forecast."
        }

    # 6. Root-cause indicators
    city_contribution = (
        df.groupby("city")["revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    product_contribution = (
        df.groupby("product_name")["revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    root_cause_indicators = {
        "highest_revenue_city": (
            str(city_contribution.index[0])
            if not city_contribution.empty else None
        ),
        "lowest_revenue_city": (
            str(city_contribution.index[-1])
            if not city_contribution.empty else None
        ),
        "highest_revenue_product": (
            str(product_contribution.index[0])
            if not product_contribution.empty else None
        ),
        "lowest_revenue_product": (
            str(product_contribution.index[-1])
            if not product_contribution.empty else None
        ),
        "interpretation": (
            "These are revenue-contribution indicators, not proof of causation."
        )
    }

    return {
        "total_revenue": total_revenue,
        "monthly_trend": monthly.to_dict("records"),
        "monthly_extrema": monthly_extrema,
        "revenue_by_city": {
            str(k): float(v) for k, v in city_revenue.items()
        },
        "revenue_by_product": {
            str(k): float(v) for k, v in product_contribution.items()
        },
        "anomalies": anomalies,
        "forecast": forecast,
        "root_cause_indicators": root_cause_indicators,
        "note": (
            "Anomalies use a basic 2-standard-deviation heuristic. "
            "Forecasting uses a simple linear trend and requires further validation."
        )
    }