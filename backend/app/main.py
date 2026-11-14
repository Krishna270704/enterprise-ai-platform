
from pathlib import Path
import shutil
import time

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import UPLOAD_DIR
from .router import route_query
from .ingestion import index_document, retrieve
from .sql_agent import ask_sql
from .analytics import run_analytics
from .evidence import fuse_evidence, verify_answer
from .llm import generate_answer
from .db import init_db


app = FastAPI(
    title="Enterprise AI Data Intelligence Platform",
    version="1.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


class Query(BaseModel):
    question: str
    source_filter: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/init-db")
def init():
    try:
        init_db()
        return {"status": "database initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    allowed_extensions = {".pdf", ".docx", ".txt", ".md", ".csv"}

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file. Use PDF, DOCX, TXT, MD or CSV."
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / filename

    try:
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        result = index_document(path)
        if result["chunks"] == 0:
            raise ValueError("The uploaded document is empty.")
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        await file.close()


@app.post("/api/query")
def query(payload: Query):
    q = payload.question.strip()

    if not q:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    start = time.perf_counter()

    route = route_query(q)

    docs = []
    sql = None
    analytics = None
    errors = []

    try:
        # Document retrieval
        if route in (
            "documents",
            "hybrid",
            "document_analytics",
            "full_hybrid"
        ):
            try:
                docs = retrieve(
                    q,
                    k=5,
                    source_filter=payload.source_filter
                )
            except Exception as e:
                errors.append({
                    "module": "documents",
                    "error": str(e)
                })

        
        # PostgreSQL SQL execution
        if route in (
            "sql",
            "hybrid",
            "sql_analytics",
            "full_hybrid"
        ):
            try:
                sql = ask_sql(q)

            except ValueError as e:
                error_message = str(e)

                errors.append({
                    "module": "sql",
                    "error": error_message
                })

                if "refund information is unavailable" in error_message.lower():
                    sql = {
                        "status": "unavailable",
                        "reason": error_message,
                        "rows": []
                    }

            except Exception as e:
                errors.append({
                    "module": "sql",
                    "error": "SQL execution failed. Check server logs."
                })


        # Analytics execution
        if route in (
            "analytics",
            "document_analytics",
            "sql_analytics",
            "full_hybrid"
        ):
            try:
                analytics = run_analytics(q)
            except Exception as e:
                errors.append({
                    "module": "analytics",
                    "error": str(e)
                })

        # Combine evidence from all successful modules
        evidence = fuse_evidence(
                document_hits=docs,
            sql_result=sql,
            analytics_result=analytics
        )

                # Generate an answer from available evidence
        refund_unavailable = (
            sql is not None
            and sql.get("status") == "unavailable"
        )

        if refund_unavailable:
            answer = (
                "Refund analysis cannot currently be performed. "
                "The PostgreSQL database does not contain a refund "
                "transactions table, refund_amount column, or "
                "refunded order status. Therefore, refund amounts "
                "and refund rates cannot be calculated. "
                "Additional refund transaction data is required."
            )
        else:
            answer = generate_answer(
                q,
                evidence,
                analytics_result=analytics,
            )

        verification = verify_answer(answer, evidence)

        return {
            "question": q,
            "route": route,
            "answer": answer,
            "evidence": evidence,
            "verification": verification,
            "latency_seconds": round(
                time.perf_counter() - start, 3
            ),
            "sql": sql,
            "analytics": analytics,
            "module_errors": errors
        }#

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
