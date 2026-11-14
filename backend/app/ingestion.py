from pathlib import Path
from functools import lru_cache
import re
import uuid

from pypdf import PdfReader
from docx import Document
from rank_bm25 import BM25Plus
from .config import CHROMA_PATH


COLLECTION_NAME = "technova_docs"


def extract_text(path):
    path = Path(path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return "\n".join(
            page.extract_text() or ""
            for page in PdfReader(str(path)).pages
        )

    if ext == ".docx":
        return "\n".join(
            paragraph.text
            for paragraph in Document(str(path)).paragraphs
        )

    if ext in {".txt", ".md", ".csv"}:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    raise ValueError(
        "Supported formats: PDF, DOCX, TXT, MD, CSV"
    )


def chunks(text, size=900, overlap=120):
    text = re.sub(r"\s+", " ", text).strip()
    output = []
    start = 0

    while start < len(text):
        end = min(len(text), start + size)
        output.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return output


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def get_reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def get_collection():
    import chromadb

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    return client.get_or_create_collection(
        COLLECTION_NAME
    )


def index_document(path):
    parts = chunks(extract_text(path))

    if not parts:
        return {
            "filename": Path(path).name,
            "chunks": 0
        }

    model = get_embedding_model()
    vectors = model.encode(
        parts,
        normalize_embeddings=True
    ).tolist()

    collection = get_collection()

    collection.upsert(
        ids=[
            str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{Path(path).resolve()}:{i}"
            ))
            for i in range(len(parts))
        ],
        documents=parts,
        embeddings=vectors,
        metadatas=[
            {
                "source": Path(path).name,
                "chunk": i
            }
            for i in range(len(parts))
        ]
    )

    return {
        "filename": Path(path).name,
        "chunks": len(parts)
    }



def retrieve(query, k=5, source_filter=None):
    collection = get_collection()
    total = collection.count()

    if total == 0:
        return []

    stored = collection.get(
        include=["documents", "metadatas"]
    )

    documents = stored["documents"] or []
    metadatas = stored["metadatas"] or []

    # Collect and deduplicate all candidate documents.
    candidates = []
    seen = set()

    for doc, meta in zip(documents, metadatas):
        if source_filter and meta.get("source") != source_filter:
            continue

        key = (
            meta.get("source"),
            meta.get("chunk"),
            doc
        )

        if key not in seen:
            seen.add(key)
            candidates.append((doc, meta))

    if not candidates:
        return []

    candidate_docs = [item[0] for item in candidates]
    candidate_meta = [item[1] for item in candidates]

    # 1. BM25 keyword retrieval
    tokenized_docs = [
        re.findall(r"\b\w+\b", doc.lower())
        for doc in candidate_docs
    ]

    tokenized_query = re.findall(
        r"\b\w+\b",
        query.lower()
    )
    stopwords = {
        "a", "an", "and", "are", "for", "from", "how", "is", "of",
        "on", "or", "the", "to", "what", "when", "where", "which",
        "who", "with",
    }
    query_terms = {
        token for token in tokenized_query
        if len(token) >= 3 and token not in stopwords
    }

    bm25 = BM25Plus(tokenized_docs)
    bm25_scores = bm25.get_scores(tokenized_query)

    # 2. Semantic retrieval
    model = get_embedding_model()

    query_vector = model.encode(
        [query],
        normalize_embeddings=True
    ).tolist()

    semantic_results = collection.query(
        query_embeddings=query_vector,
        n_results=min(max(k * 3, 10), total),
        where={"source": source_filter} if source_filter else None
    )

    semantic_scores = {}

    for doc, meta, distance in zip(
        semantic_results["documents"][0],
        semantic_results["metadatas"][0],
        semantic_results["distances"][0]
    ):
        key = (
            meta.get("source"),
            meta.get("chunk")
        )

        semantic_scores[key] = 1.0 / (
            1.0 + max(0.0, float(distance))
        )

    # 3. Normalize BM25 scores and calculate hybrid scores
    max_bm25 = max(bm25_scores) if len(bm25_scores) else 0

    results = []

    for doc, meta, bm25_score in zip(
        candidate_docs,
        candidate_meta,
        bm25_scores
    ):
        key = (
            meta.get("source"),
            meta.get("chunk")
        )

        normalized_bm25 = (
            float(bm25_score) / max_bm25
            if max_bm25 > 0 else 0.0
        )

        semantic_score = semantic_scores.get(key, 0.0)
        document_terms = set(
            re.findall(r"\b\w+\b", doc.lower())
        )
        lexical_overlap = query_terms & document_terms

        # BM25Plus assigns non-zero scores even when no query term occurs in
        # a document. Do not return those false positives unless semantic
        # retrieval provides a strong independent signal.
        if query_terms and not lexical_overlap and semantic_score < 0.55:
            continue

        hybrid_score = (
            0.5 * normalized_bm25
            + 0.5 * semantic_score
        )

        results.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "chunk": meta.get("chunk"),
            "bm25_score": round(float(normalized_bm25), 4),
            "semantic_score": round(semantic_score, 4),
            "score": round(float(hybrid_score), 4)
        })

    # 4. Select hybrid candidates
    candidates = sorted(
        results,
        key=lambda item: item["score"],
        reverse=True
    )[:max(k * 3, 10)]

    if not candidates:
        return []

    # 5. Cross-encoder reranking
    reranker = get_reranker()

    pairs = [
        (query, item["text"])
        for item in candidates
    ]

    rerank_scores = reranker.predict(pairs)

    for item, rerank_score in zip(candidates, rerank_scores):
        item["rerank_score"] = round(
            float(rerank_score), 4
        )

    return sorted(
        candidates,
        key=lambda item: item["rerank_score"],
        reverse=True
    )[:k]
