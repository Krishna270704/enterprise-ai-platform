# TechNova Enterprise AI Data Intelligence Platform

> **Ask your data. Trust the evidence.**

An evidence-grounded enterprise intelligence workspace that lets users ask natural-language questions across company documents, PostgreSQL business data, and sales analytics. Every response exposes its route, latency, supporting evidence, SQL output, analytics output, and a verification status so users can inspect how an answer was produced.

> **Academic project notice:** TechNova records and documents are synthetic demo data. This repository demonstrates an extensible architecture and evaluation workflow; it is not a production decision-making system.

<p align="center">
  <img src="reports/screenshots/platform-landing.png" alt="TechNova platform landing page" width="820">
</p>

## Why this project?

Enterprise information is usually split across unstructured documents, relational databases, and analytical workflows. This platform brings those sources behind one conversational interface while keeping the evidence visible:

- Ask questions in plain English instead of writing SQL or searching folders.
- Route each question to the most relevant capability: documents, SQL, analytics, or a hybrid combination.
- Upload PDF, DOCX, TXT, Markdown, and CSV files and index them for retrieval.
- Inspect the evidence used to generate an answer.
- See SQL and analytics payloads rather than receiving an opaque text-only response.
- Run the complete stack locally with a React frontend, FastAPI backend, PostgreSQL, ChromaDB, and Groq.

## Highlights

| Capability | What it does |
| --- | --- |
| **Adaptive query routing** | Classifies questions into `documents`, `sql`, `analytics`, `hybrid`, `document_analytics`, `sql_analytics`, or `full_hybrid`. |
| **Document intelligence** | Extracts and chunks PDF, DOCX, TXT, MD, and CSV files, then stores embeddings in ChromaDB for semantic retrieval. |
| **Natural-language SQL** | Converts supported business questions into read-oriented PostgreSQL queries and returns structured rows. |
| **Business analytics** | Calculates total revenue, monthly trends, city and product contribution, basic anomalies, experimental forecasts, and contribution indicators. |
| **Evidence fusion** | Combines document hits, SQL results, and analytics results into a single evidence bundle. |
| **Answer verification** | Applies a transparent lexical-overlap heuristic and reports the verification status alongside the answer. |
| **Inspectable UI** | Displays route, latency, answer, evidence sources, SQL output, analytics output, and module warnings. |

## Architecture

```mermaid
flowchart LR
    U[User] --> UI[React + Vite UI]
    UI --> API[FastAPI API]
    API --> R[Adaptive Query Router]
    R --> D[Document Retrieval]
    R --> S[PostgreSQL SQL Agent]
    R --> A[Analytics Engine]
    D --> C[(ChromaDB)]
    S --> P[(PostgreSQL)]
    A --> P
    D --> F[Evidence Fusion]
    S --> F
    A --> F
    F --> L[Groq Answer Generation]
    L --> V[Heuristic Verification]
    V --> UI
```

### Request lifecycle

1. The frontend sends a question to `POST /api/query`.
2. The router identifies the required data sources.
3. The selected modules retrieve documents, execute SQL, and/or run analytics.
4. Evidence is fused into a common response context.
5. Groq generates a response from the available evidence.
6. A verification heuristic checks lexical support and the UI presents the full trace.

## Screenshots

<p align="center">
  <img src="reports/screenshots/platform-full-hybrid.png" alt="Full hybrid query response" width="820">
</p>

<p align="center">
  <img src="reports/screenshots/evidence-sources.png" alt="Evidence sources panel" width="400">
  <img src="reports/screenshots/monthly-sales-analytics.png" alt="Monthly sales analytics" width="400">
</p>

## Technology stack

- **Frontend:** React 18, Vite, Axios, React Markdown, remark-gfm
- **API:** FastAPI, Uvicorn, Pydantic, Python 3.10-3.12
- **Data:** PostgreSQL, pandas, NumPy
- **Retrieval:** ChromaDB, sentence-transformers
- **Document parsing:** pypdf, python-docx, CSV support
- **LLM integration:** Groq API
- **Validation:** pytest

## Quick start on Windows

### Prerequisites

- Windows 10 or 11
- Python 3.10-3.12
- Node.js 18+
- PostgreSQL 14+
- A Groq API key

### 1. Clone the repository

```powershell
git clone https://github.com/Krishna270704/enterprise-ai-platform.git
cd enterprise-ai-platform
```

### 2. Create and configure the Python environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item backend\.env.example backend\.env
pip install -r backend\requirements.txt
```

Open `backend\.env` and set your credentials:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/enterprise_ai
CHROMA_PATH=../data/chroma
UPLOAD_DIR=../data/uploads
```

Create the PostgreSQL database before loading data:

```powershell
createdb enterprise_ai
```

Alternatively, create a database named `enterprise_ai` in pgAdmin.

### 3. Generate and load the demo data

From the project root:

```powershell
python scripts\generate_demo_data.py
python scripts\load_demo_data.py
python scripts\index_demo_documents.py
```

These commands populate the synthetic TechNova tables and index the sample documents in `data\raw\documents`.

### 4. Start the backend

Open a terminal at the project root:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="backend"
uvicorn app.main:app --app-dir backend --reload
```

- API: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

### 5. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## API reference

### `GET /api/health`

Returns a service health response:

```json
{
  "status": "ok"
}
```

### `POST /api/init-db`

Initializes the PostgreSQL schema used by the demo.

### `POST /api/upload`

Uploads and indexes one supported document. Supported extensions:

```text
.pdf  .docx  .txt  .md  .csv
```

### `POST /api/query`

Request:

```json
{
  "question": "According to the return policy, how many customers are in the database?",
  "source_filter": null
}
```

The response includes:

```text
question
route
answer
evidence
verification
latency_seconds
sql
analytics
module_errors
```

## Example questions

Try these from the UI:

- `What is the return policy?`
- `How many customers are there?`
- `Show monthly sales trend`
- `Which city has the highest revenue?`
- `According to the refund policy, how many customers are in the database, and what is the monthly sales trend?`
- `Upload a policy document, then ask a question about it`

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── analytics.py       # Revenue trends, anomalies, forecast, indicators
│   │   ├── db.py              # PostgreSQL connection and query helpers
│   │   ├── evidence.py        # Evidence fusion and answer verification
│   │   ├── ingestion.py       # File extraction, chunking, retrieval
│   │   ├── llm.py             # Groq answer generation
│   │   ├── main.py            # FastAPI application and endpoints
│   │   ├── router.py          # Keyword-based capability routing
│   │   └── sql_agent.py       # Natural-language SQL workflow
│   └── requirements.txt
├── data/
│   ├── raw/documents/         # Synthetic policy and business documents
│   └── sample_data/           # Synthetic CSV source data
├── frontend/
│   └── src/                   # React application
├── reports/                   # Evaluation outputs and screenshots
├── scripts/                   # Data generation, loading, indexing, evaluation
└── tests/                     # Backend and integration-focused tests
```

## Testing

Run the test suite from the project root:

```powershell
pytest
```

The repository also includes evaluation and validation scripts:

```powershell
python scripts\evaluate_retrieval.py
python scripts\run_priority_validation.py
python scripts\run_research_evaluation.py
```

Generated reports are stored in the repository's root and `reports\` directory for inspection.

## Design boundaries and limitations

This is a runnable academic baseline. Important limitations are intentionally documented:

- Routing currently uses keyword rules rather than a trained intent classifier.
- Verification uses lexical overlap; it is not semantic entailment or a guarantee of factual correctness.
- SQL safety checks are not a complete database sandbox.
- Forecasting uses a simple linear trend and is explicitly experimental.
- Anomaly detection uses a basic two-standard-deviation heuristic.
- Revenue contribution indicators should not be interpreted as causal root-cause analysis.
- Forecasting, causal analysis, and production-grade evaluation require additional validated implementations.
- Do not place real confidential data or production credentials in this demo without adding appropriate security, access control, auditing, and deployment hardening.

## Evaluation philosophy

The project keeps evaluation artifacts visible instead of presenting unverified claims. A serious deployment should measure, on a labelled test set:

- Answer accuracy
- Retrieval Precision@k and recall
- Evidence faithfulness
- Hallucination rate
- SQL generation and execution accuracy
- Route classification accuracy
- End-to-end latency

See the existing reports in [`reports/`](reports/) and the validation documents in the repository root for the current synthetic-data results and known gaps.

## Contributing

1. Create a feature branch.
2. Make a focused change with tests where behavior changes.
3. Run `pytest` and the relevant frontend build.
4. Update documentation for user-visible changes.
5. Open a pull request describing the evidence and validation performed.

## License

This repository does not currently declare a formal open-source license. Contact the repository owner before redistributing or using it outside the intended academic/demo context.
