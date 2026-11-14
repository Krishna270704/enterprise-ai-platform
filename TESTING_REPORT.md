# Enterprise AI Data Intelligence Platform - Testing Report

Date: 2026-11-11

## Executive summary

The existing implementation was tested without changing the PostgreSQL schema or
existing records. The final automated backend suite contains **28 tests: 28
passed, 0 failed, 0 blocked**. The React production build also passed. The
earlier 27-test count predates the focused `full_hybrid` regression test.

The higher-priority research experiments are documented separately in
[RESEARCH_VALIDATION_REPORT.md](./RESEARCH_VALIDATION_REPORT.md), with
reproducible CSV artifacts for retrieval, SQL, and analytics.

Two implementation defects were fixed:

1. Retrieval returned low-relevance documents because BM25Plus can assign
   non-zero scores when no query term occurs in a document. Retrieval now
   requires meaningful lexical overlap or a strong semantic score.
2. The low-level database helper accepted and committed non-SELECT statements.
   `select_rows()` now rejects non-SELECT statements, comments, and multiple
   statements before opening a database connection.

Additional hardening:

- Chroma indexing uses idempotent `upsert`, so duplicate uploads do not create
  duplicate chunks.
- Empty document uploads now return HTTP 400 instead of reporting a successful
  zero-chunk index.
- Document verification rejects unsupported numeric claims and uses a stricter
  lexical support threshold.

## Commands executed

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests -v
.\.venv\Scripts\python.exe -m compileall -q backend
npm --prefix frontend run build
```

Result: `27 passed in 5.11s`; backend compilation passed; Vite build passed.

## Database validation

| Check | Result |
|---|---|
| Application connection | Passed; database `enterprise_ai_demo`, PostgreSQL port 5432 |
| Table schemas | Passed; six expected tables and expected columns present |
| Row counts | Passed: customers 30, employees 15, products 6, orders 120, sales 120, inventory 6 |
| Total records | Passed: 297 |
| Foreign keys | Passed: orders -> customers; sales -> orders/products; inventory -> products |
| Direct SELECT queries | Passed |
| Non-SELECT execution | Passed rejection after fix |
| Data mutation | No records were truncated, dropped, recreated, or overwritten |

## Text-to-SQL and SQL safety

The existing SQL tests passed for counts, delivered-order revenue, validation,
unknown tables, destructive statements, and multiple statements. Actual
PostgreSQL execution matched the independent expected values:

- Customers: 30
- Employees: 15
- Products: 6
- Delivered-order revenue: 5,353,600

The lower-level `select_rows()` write guard was added and covered by a
regression test. Provider-generated SQL depends on Groq availability; no
provider 429 occurred during the executed checks.

## Document ingestion and ChromaDB

| Format/check | Result |
|---|---|
| TXT extraction | Passed |
| MD extraction | Passed |
| CSV extraction | Passed |
| DOCX extraction | Passed |
| PDF extraction | Passed with a temporary non-empty PDF; extracted text was indexed and retrieved |
| Unsupported extension | Passed; HTTP 400 |
| Empty upload | Passed; HTTP 400 |
| Duplicate upload | Passed; two uploads returned HTTP 200 without duplicate chunk creation |
| Chroma indexing | Passed; chunks were indexed and temporary audit chunks were removed |
| Source filtering | Passed for `HR_Policy.txt` |
| Top-k retrieval | Passed |

The casual-leave retrieval regression now excludes unrelated policies when they
have no meaningful query-term overlap and weak semantic similarity. The focused
`full_hybrid` regression test verifies that document, database, and analytics
modules all execute and that the route returns all required evidence types.

## RAG, evidence, and answer grounding

The casual-leave API query returned the HR policy source and a verification
status of `review_required` for an answer containing unsupported/excess wording,
rather than treating the answer as fully supported. Numeric evidence tests
passed for both supported and unsupported values.

Evidence fusion tests passed for document, database, duplicate, and empty
evidence. Monthly analytics extrema correction tests passed and rejected
incorrect maximum/minimum claims.

Remaining limitation: verification is still lexical/numeric heuristic
verification, not a formal entailment model. It can require human review for
valid paraphrases and cannot prove complete factual correctness.

## Analytics

Analytics tests passed for monthly aggregation, maximum/minimum month
calculation, and generated-answer extrema correction. Direct database-backed
analytics queries executed successfully for monthly sales trend questions.

The implementation also exposes city/product contribution, anomaly indicators,
and a linear forecast. The forecast is explicitly labelled experimental and was
not treated as a validated prediction. No claim of forecast accuracy was made.

## Query router

All seven routes were exercised with representative questions:

| Route | Result |
|---|---|
| documents | Passed |
| sql | Passed |
| analytics | Passed |
| hybrid | Passed |
| document_analytics | Passed |
| sql_analytics | Passed |
| full_hybrid | Passed |

The live API returned successful answers for document, SQL, and analytics
queries with no module errors.

## FastAPI

| Endpoint/check | Result |
|---|---|
| `GET /api/health` | HTTP 200 |
| `POST /api/init-db` | HTTP 200; idempotent initialization |
| `POST /api/upload` valid file | HTTP 200 |
| `POST /api/upload` unsupported file | HTTP 400 |
| `POST /api/upload` empty file | HTTP 400 |
| `POST /api/query` empty question | HTTP 400 |
| `POST /api/query` document question | Successful response with answer, evidence, verification, latency, and module errors fields |
| `POST /api/query` SQL question | Successful response with SQL rows |
| `POST /api/query` analytics question | Successful response with analytics payload |

Provider-rate-limit behavior was not observed during testing, so HTTP 429
handling remains unvalidated rather than being marked passed.

## Frontend integration

`npm --prefix frontend run build` passed. Inspection confirmed:

- API base URL is `http://127.0.0.1:8000`.
- Upload uses `POST /api/upload`.
- Queries use `POST /api/query`.
- SQL, analytics, evidence, verification, loading, and error states are
  rendered.

No browser automation was available in this test run, so browser-level click
and rendering behavior remains a manual follow-up. The frontend was not
rebuilt or functionally redesigned.

## Remaining implementation gaps

- Evidence verification is heuristic, not semantic entailment.
- Groq provider failure and HTTP 429 paths need a controlled integration test
  with a mock provider.
- Forecasting and anomaly detection are descriptive/experimental and require
  a labelled validation set before research claims.
- SQL validation is a conservative application guard, not a complete database
  sandbox.
- The frontend API URL is hardcoded rather than environment-configurable.
- Full browser upload/query interaction was not automated.

## Reproduction

1. Configure `backend/.env` with the existing database and provider settings.
2. Start the API:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

3. Run backend tests and frontend build:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest .\tests -v
   npm --prefix frontend run build
   ```

4. Check `GET http://127.0.0.1:8000/api/health` and use the API endpoints
   listed above.
