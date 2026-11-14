# Enterprise AI Data Intelligence Platform
Academic implementation of **Enterprise AI Data Intelligence Platform for Evidence-Grounded Analytics and Decision Support**.

> TechNova records and documents generated here are synthetic demo data, not real company records.

## Architecture
React → FastAPI → adaptive query router → document retrieval / PostgreSQL NL-to-SQL / analytics → evidence fusion → Groq response → heuristic evidence verification.

## Requirements
Windows 10/11, VS Code, Python 3.10–3.12, Node.js 18+, PostgreSQL 14+, Internet access.

## Setup (PowerShell, from project root)
```powershell
py -m venv .venv
./.venv/Scripts/Activate.ps1
Copy-Item backend/.env.example backend/.env
pip install -r backend/requirements.txt
```
Edit `backend/.env`: set your PostgreSQL password in `DATABASE_URL` and add `GROQ_API_KEY`. Create a PostgreSQL database named `technova` using pgAdmin or `createdb technova`.

Generate and load data:
```powershell
python scripts/generate_demo_data.py
python scripts/load_demo_data.py
python scripts/index_demo_documents.py
```
Start API (terminal 1):
```powershell
$env:PYTHONPATH="backend"
uvicorn app.main:app --app-dir backend --reload
```
API docs: http://127.0.0.1:8000/docs

Start UI (terminal 2):
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

Tests (project root): `pytest`

## Example questions
- What is the return policy?
- How many customers are there?
- Show monthly sales trend.

## Implementation and research limitations
This is a runnable baseline, not a claim that every research objective is fully validated. It includes PDF/DOCX/TXT/MD/CSV extraction, chunking, ChromaDB embeddings, semantic retrieval with simple keyword reranking, keyword-rule routing, Groq NL-to-SQL with basic read-only checks, descriptive sales analytics and a simple outlier heuristic, evidence fusion, and lexical-overlap verification. Lexical verification is not semantic entailment; the SQL checks are not a complete sandbox. Forecasting and causal root-cause analysis need additional validated implementation. Build a labelled evaluation set and report actual answer accuracy, Precision@k, faithfulness, hallucination rate, SQL accuracy and latency—never fabricate results.
