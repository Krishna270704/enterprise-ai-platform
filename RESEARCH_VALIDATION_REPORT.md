# Research Validation Report

Date: 2026-11-11

## Scope and methodology

This report contains newly executed controlled experiments, separate from the
previous 28-test regression baseline. The experiments used the existing
synthetic TechNova documents and the existing `enterprise_ai_demo` PostgreSQL
database. No schema changes or destructive database operations were performed.

The reproducible runner is
[run_priority_validation.py](<C:/Users/KRISHNA/OneDrive/Desktop/Minor%20project/enterprise-ai-data-intelligence/scripts/run_priority_validation.py>).
Run it from the project root with the API available:

```powershell
$env:PYTHONPATH="backend"
$env:API_URL="http://127.0.0.1:8000"
.\.venv\Scripts\python.exe .\scripts\run_priority_validation.py
```

The runner writes:

- [RAG_EVALUATION_RESULTS.csv](<C:/Users/KRISHNA/OneDrive/Desktop/Minor%20project/enterprise-ai-data-intelligence/RAG_EVALUATION_RESULTS.csv>)
- [SQL_EVALUATION_RESULTS.csv](<C:/Users/KRISHNA/OneDrive/Desktop/Minor%20project/enterprise-ai-data-intelligence/SQL_EVALUATION_RESULTS.csv>)
- [ANALYTICS_VALIDATION_RESULTS.csv](<C:/Users/KRISHNA/OneDrive/Desktop/Minor%20project/enterprise-ai-data-intelligence/ANALYTICS_VALIDATION_RESULTS.csv>)
- `priority_validation_raw.json`

## RAG evaluation

Ten manually labelled questions were evaluated against the five specified
documents. Each question had one relevant source document. Retrieval used
`k=5`. Temporary fixtures used a unique per-run UUID in every Chroma source
name; cleanup deleted only those exact source names. No generic filename
cleanup is used.

| Metric | Measured result |
|---|---:|
| Questions | 10 |
| Precision@5 | 0.2000 |
| Mean precision over returned documents | 0.8333 |
| Recall@5 | 1.0000 |
| MRR | 1.0000 |

**Precision@5** is the number of relevant documents in the first five ranks
divided by fixed `k=5`, including when fewer than five documents are returned.
**Precision over returned documents** divides by the actual number returned.
**Recall@5** is the number of relevant documents found in the first five ranks
divided by the number of labelled relevant documents. **MRR** is the reciprocal
rank of the first relevant result, averaged across questions.

Recall and reciprocal rank were perfect for this small synthetic benchmark, but
three queries returned irrelevant documents. Those rows are reported as
`REVIEW_REQUIRED`, not fully successful. These results do not establish
general-domain retrieval performance.

## Answer faithfulness

The exact question “What is the process for taking casual leave?” was tested
through the running API. The response cited `HR_Policy.txt` and stated only:

- submit the HR request through the employee portal;
- obtain manager approval.

The experiment detected no unsupported payroll linkage. The verification result
was `review_required`, correctly reflecting that the verifier remains a
heuristic rather than a semantic entailment system.

Controlled verifier cases: **4/4 passed**:

- supported document claim;
- unsupported document claim;
- unsupported numerical claim;
- missing evidence.

The verifier test is behavioral validation, not a measured hallucination rate.

## Document ingestion

Temporary, non-project files were used to exercise TXT, MD, CSV, DOCX, and a
library-generated non-empty PDF. Extraction and chunk creation succeeded for
all five formats. The run used unique source names and removed only the exact
five names created by that run. Existing Chroma records were verified intact:
19 records before and 19 after, including unchanged counts for the five
specified source documents.

Source filtering, duplicate upload idempotency, unsupported extension
rejection, and empty upload rejection were also exercised.

Original documents and the existing Chroma collection were not cleared.

## Text-to-SQL

Ten controlled natural-language questions were generated through the existing
Groq SQL integration, validated, executed against PostgreSQL, and compared
with independently executed equivalent SQL:

- customer count;
- employee count;
- product count;
- order count;
- delivered-order count;
- total revenue;
- monthly revenue;
- city-wise revenue;
- product-wise revenue;
- inventory below reorder level.

Result: **10/10 correct, accuracy 1.0000**. Equivalence comparison normalized
generated aliases, date representations, and harmless additional projected
columns while comparing the requested values.

SQL safety probes: **8/8 rejected**, covering INSERT, UPDATE, DELETE, DROP,
multiple statements, unknown tables, comments, and a PostgreSQL sleep function.

## Analytics validation

Application output was compared with direct PostgreSQL results for:

- monthly revenue;
- maximum month;
- minimum month;
- city-wise revenue;
- product-wise revenue;
- anomaly indicators.

Result: **6/6 passed, 0 failed**. The forecast output was present but classified
as `EXPERIMENTAL_UNVALIDATED` because no labelled future observations exist.
No forecast accuracy was calculated or claimed.

## Hybrid routing and evidence fusion

All seven routes were tested through the running API. All seven selected routes executed the required evidence modules and returned
no module errors in the fresh API process used for the final run:

| Route | Result |
|---|---|
| documents | PASS |
| sql | PASS |
| analytics | PASS |
| hybrid | PASS |
| document_analytics | PASS |
| sql_analytics | PASS |
| full_hybrid | PASS |

This validates execution and evidence-type presence for all seven cases; a
correct route label is not treated as sufficient because HTTP status, evidence
types, and module errors are also required for the route pass boolean.

## Full-hybrid incident investigation

The earlier `full_hybrid` failure artifact contained only the API's sanitized
message `SQL execution failed. Check server logs.` It contained no exception
type or traceback, so no more specific historical exception can be claimed
from that artifact. Reproducing the exact question directly through
`ask_sql()` produced valid SQL and rows. Reproducing it through a fresh
FastAPI process on port 8002 also returned HTTP 200 with document, database,
and analytics evidence and no module errors. Port 8000 was no longer listening
when inspected, so the earlier failure was isolated to the prior API
process/provider state and was not reproducible as an application-code defect.

A focused regression test now verifies that a full-hybrid request executes all
three modules and returns the three required evidence types. The final
priority validation run reports `full_hybrid` as PASS.

## Implementation improvements

- Added question-focused document sentence filtering before LLM answer
  generation, preventing unrelated payroll facts in the casual-leave answer.
- Added `revenue_by_product` to analytics output so product-wise analytics can
  be independently validated.
- Added the reproducible 10-question retrieval/SQL/analytics validation runner.

## Limitations

- The RAG set is a ten-question synthetic benchmark, not a statistically
  representative evaluation set.
- Evidence verification uses lexical and numeric heuristics, not semantic
  entailment or claim decomposition.
- Groq-dependent results can be blocked by provider errors or HTTP 429; no 429
  occurred in this run.
- Forecasting remains experimental and unvalidated.
- Browser-level frontend interactions were not part of this CLI experiment.

## Final measured experiment totals

Across the new controlled experiments:

- RAG: 10 evaluated, 10 relevant documents found in top-5, 0 blocked.
- SQL: 10 evaluated, 10 correct, 0 blocked.
- SQL safety: 8 probes, 8 rejected correctly.
- Analytics: 6 validated metrics passed, 1 forecast classified unvalidated.
- Verifier: 4 behavioral cases passed.
- API routes: 7/7 passed in the fresh final API process.

These totals are experiment-specific and must not be presented as universal
platform accuracy.
