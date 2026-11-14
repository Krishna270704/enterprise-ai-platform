
import re


NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}


def _claim_numbers(text):
    numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", str(text).lower()))
    words = re.findall(r"\b[a-z]+\b", str(text).lower())
    numbers.update(NUMBER_WORDS[word] for word in words if word in NUMBER_WORDS)
    return numbers


def fuse_evidence(document_hits=None, sql_result=None, analytics_result=None):
    out = []
    seen_documents = set()

    for item in document_hits or []:
        source = item.get("source", "unknown")
        content = item.get("text", "")

        # Remove repeated copies of identical document evidence
        key = (source, re.sub(r"\s+", " ", content).strip().lower())

        if not content or key in seen_documents:
            continue

        seen_documents.add(key)

        out.append({
            "type": "document",
            "source": source,
            "content": content,
            "score": item.get("score")
        })

    if sql_result:
        out.append({
            "type": "database",
            "source": "PostgreSQL",
            "content": sql_result
        })

    if analytics_result:
        out.append({
            "type": "analytics",
            "source": "TechNova sales tables",
            "content": analytics_result
        })

    return out


def verify_answer(answer, evidence):
    if not evidence:
        return {
            "support_ratio": 0.0,
            "status": "insufficient_evidence",
            "method": "evidence availability check"
        }

    answer = str(answer)
    database_evidence = [
        item for item in evidence if item.get("type") == "database"
    ]
    analytics_evidence = [
        item for item in evidence if item.get("type") == "analytics"
    ]
    document_evidence = [
        item for item in evidence if item.get("type") == "document"
    ]

    # Check numeric claims against structured database/analytics evidence.
    answer_numbers = _claim_numbers(answer)
    evidence_text = " ".join(
        str(item.get("content", "")) for item in evidence
    )
    evidence_numbers = _claim_numbers(evidence_text)

    if answer_numbers and not answer_numbers.issubset(evidence_numbers):
        return {
            "support_ratio": round(
                len(answer_numbers & evidence_numbers) / len(answer_numbers),
                3,
            ),
            "status": "review_required",
            "method": "numeric claim matching against evidence; human review required",
        }

    if database_evidence or analytics_evidence:
        if answer_numbers:
            matched = answer_numbers & evidence_numbers
            ratio = len(matched) / len(answer_numbers)

            return {
                "support_ratio": round(ratio, 3),
                "status": "supported" if ratio == 1 else "review_required",
                "method": "numeric claim matching against structured evidence; human review required"
            }

        return {
            "support_ratio": 0.5,
            "status": "review_required",
            "method": "structured evidence available; semantic verification not implemented"
        }

    # Basic lexical comparison for document-grounded answers.
    corpus = evidence_text.lower()
    words = [
        word.strip(".,!?;:()[]{}\"'")
        for word in answer.lower().split()
        if len(word) > 4
    ]

    if not words:
        return {
            "support_ratio": 0.0,
            "status": "review_required",
            "method": "lexical overlap heuristic; human review required"
        }

    matched = sum(word in corpus for word in words)
    score = matched / len(words)

    return {
        "support_ratio": round(score, 3),
        "status": "supported" if score >= 0.8 else "review_required",
        "method": "lexical overlap heuristic; human review required"
    }
