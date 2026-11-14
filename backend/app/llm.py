
import re
from datetime import datetime
from typing import Any

from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL


SYSTEM_PROMPT = """
You are the answer-generation engine of an Enterprise AI
Data Intelligence Platform.

STRICT RULES:

1. Answer using ONLY the supplied evidence.
2. Never invent facts, figures, dates, currencies or business events.
3. Do not assume revenue is USD, INR or any other currency
   unless the evidence explicitly defines it.
4. If currency is unspecified, use the neutral term
   "revenue units".
5. Clearly distinguish recorded facts from interpretations
   and recommendations.
6. Never claim that correlation proves causation.
7. Never infer that zero recorded transactions proves that
   a business policy has no financial impact.
8. If the database has no relevant records, explicitly
   state that the available data does not establish the claim.
9. If evidence is conflicting, explain the conflict.
10. Cite document filenames or PostgreSQL and analytics
    source names where relevant.
11. Do not present experimental forecasts as guaranteed
    predictions.
12. If evidence is insufficient, clearly say so.
13. For document questions, include only statements that directly answer the
    question. Omit unrelated statements from the same document chunk, even if
    they are factually present in the evidence.

14. For monthly revenue, use the supplied structured monthly facts as the
    authority for every figure and for the maximum/minimum month. Do not
    infer, recalculate, or substitute a month or revenue value.
15. If your draft conflicts with the structured monthly extrema, do not state
    the conflicting interpretation; correct it before responding.

Use clear headings and concise tables when useful.
"""


def focus_document_evidence(question: str, evidence: list[dict]) -> list[dict]:
    """Keep document sentences relevant to the requested topic."""

    stopwords = {
        "about", "are", "for", "from", "how", "is", "the", "what",
        "when", "where", "which", "who", "with",
    }
    question_terms = {
        term
        for term in re.findall(r"\b[a-z]{3,}\b", question.lower())
        if term not in stopwords
    }
    process_question = bool(
        question_terms
        & {"process", "steps", "taking", "submit", "request"}
    )
    process_terms = {
        "approval", "approv", "leave", "portal", "request",
        "submit", "taking",
    }
    focused = []

    for item in evidence:
        if item.get("type") != "document":
            focused.append(item)
            continue

        content = str(item.get("content", ""))
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", content)
            if sentence.strip()
        ]
        if not sentences:
            focused.append(item)
            continue

        selected = []
        for sentence in sentences:
            terms = {
                term
                for term in re.findall(r"\b[a-z]{3,}\b", sentence.lower())
                if term not in stopwords
            }
            if terms & question_terms or (process_question and terms & process_terms):
                selected.append(sentence)

        if selected:
            focused.append({**item, "content": " ".join(selected)})
        else:
            focused.append(item)

    return focused


def _number_text(value: Any) -> str:
    return str(float(value)).rstrip("0").rstrip(".")


def _extremum_claim_supported(
    answer: str,
    words: tuple[str, ...],
    month: str,
    revenue: float,
) -> bool:
    text = (
        str(answer)
        .lower()
        .replace(",", "")
        .replace("\u2011", "-")
        .replace("\u202f", " ")
    )
    month_name = datetime.strptime(month, "%Y-%m").strftime("%B").lower()
    value = _number_text(revenue)
    pattern = "|".join(re.escape(word) for word in words)
    for match in re.finditer(rf"\b(?:{pattern})\b", text):
        context = text[max(0, match.start() - 140):match.end() + 140]
        if (
            re.search(rf"(?:{re.escape(month)}|{month_name})", context)
            and value in context
        ):
            return True
    return False


def monthly_extrema_are_supported(answer: str, analytics_result: dict) -> bool:
    """Reject generated answers with contradictory monthly extrema claims."""

    extrema = analytics_result.get("monthly_extrema")
    if not extrema:
        return True

    maximum = extrema["maximum"]
    minimum = extrema["minimum"]
    return (
        _extremum_claim_supported(
            answer,
            ("high", "highest", "maximum", "max", "peak", "peaks"),
            maximum["month"],
            maximum["revenue"],
        )
        or not any(
            word in answer.lower()
            for word in ("high", "highest", "maximum", "max", "peak", "peaks")
        )
    ) and (
        _extremum_claim_supported(
            answer,
            ("low", "lowest", "minimum", "min", "trough", "troughs"),
            minimum["month"],
            minimum["revenue"],
        )
        or not any(
            word in answer.lower()
            for word in ("low", "lowest", "minimum", "min", "trough", "troughs")
        )
    )


def _deterministic_analytics_correction(
    analytics_result: dict,
) -> str:
    maximum = analytics_result["monthly_extrema"]["maximum"]
    minimum = analytics_result["monthly_extrema"]["minimum"]
    return (
        "**Monthly Sales Trend (verified)**\n\n"
        f"- Highest recorded month: {maximum['month']} "
        f"({maximum['revenue']:,.0f} revenue units).\n"
        f"- Lowest recorded month: {minimum['month']} "
        f"({minimum['revenue']:,.0f} revenue units).\n\n"
        "These extrema are calculated directly from the supplied monthly "
        "sales evidence (source: TechNova sales tables); no causal "
        "interpretation is made."
    )


def generate_answer(question, evidence, analytics_result=None):
    if not evidence:
        return (
            "Insufficient evidence. Upload relevant documents "
            "or load the demo database."
        )

    if not GROQ_API_KEY:
        return (
            "Groq API key is not configured. "
            "Retrieved evidence: " + str(evidence)[:3000]
        )

    analytics_result = analytics_result or {}
    structured_facts = {
        "monthly_trend": analytics_result.get("monthly_trend", []),
        "monthly_extrema": analytics_result.get("monthly_extrema"),
    }

    focused_evidence = focus_document_evidence(question, evidence)
    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Available evidence:\n{focused_evidence}\n\n"
                    f"Structured analytics facts (authoritative):\n"
                    f"{structured_facts}\n\n"
                    "Generate an evidence-grounded answer."
                )
            }
        ],
        temperature=0.1
    )

    answer = response.choices[0].message.content or ""
    if analytics_result and not monthly_extrema_are_supported(
        answer,
        analytics_result,
    ):
        return _deterministic_analytics_correction(analytics_result)

    return answer
