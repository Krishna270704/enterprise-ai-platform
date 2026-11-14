
import React, { useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API = "http://127.0.0.1:8000";

function cleanText(value = "") {
  return String(value)
    .replace(/âCustomers/g, "Customers")
    .replace(/monthâtoâmonth/g, "month-to-month")
    .replace(/â†’/g, "->")
    .replace(/Â·/g, "|")
    .replace(/â¯/g, " ")
    .replace(/\u00A0/g, " ");
}

export default function App() {
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function ask(e) {
    e.preventDefault();
    if (!q.trim()) return;

    setBusy(true);
    setMsg("");
    setData(null);

    try {
      const response = await axios.post(`${API}/api/query`, {
        question: q
      });
      setData(response.data);
    } catch (error) {
      setMsg(error.response?.data?.detail || error.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setMsg("Uploading and indexing document...");

    try {
      const response = await axios.post(
        `${API}/api/upload`,
        formData
      );
      setMsg(
        `Successfully indexed ${response.data.chunks} chunks from ${response.data.filename}`
      );
    } catch (error) {
      setMsg(error.response?.data?.detail || error.message);
    }

    e.target.value = "";
  }

  const samples = [
    "What is the return policy?",
    "How many customers are there?",
    "Show monthly sales trend",
    "According to the refund policy, how many customers are in the database, and what is the monthly sales trend?"
  ];

  return (
    <main>
      <header>
        <small>TECHNOVA | ENTERPRISE INTELLIGENCE</small>
        <h1>
          Ask your data.
          <br />
          <span>Trust the evidence.</span>
        </h1>
        <p>
          Natural-language access to enterprise documents,
          PostgreSQL and analytics.
        </p>
      </header>

      <section>
        <h2>Ask a question</h2>

        <form onSubmit={ask}>
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask a question about your documents or business data..."
          />

          <button type="submit" disabled={busy}>
            {busy ? "Processing..." : "Run query ->"}
          </button>
        </form>

        <div className="samples">
          {samples.map((sample) => (
            <button
              className="secondary"
              key={sample}
              type="button"
              onClick={() => setQ(sample)}
            >
              {sample}
            </button>
          ))}
        </div>

        <label className="upload">
          Upload PDF / DOCX / TXT / CSV
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md,.csv"
            onChange={upload}
          />
        </label>

        {msg && <p className="message">{msg}</p>}
      </section>

      {data && (
        <>
          <section>
            <div className="result-meta">
              <span>ROUTE: {data.route}</span>
              <span>LATENCY: {data.latency_seconds}s</span>
              <span>VERIFICATION: {data.verification?.status || "N/A"}</span>
            </div>

            <h2>Generated answer</h2>
            <div className="answer">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {cleanText(data.answer)}
              </ReactMarkdown>
            </div>

            <p className="disclaimer">
              Verification uses a heuristic and does not guarantee
              factual correctness. Review the supporting evidence.
            </p>
          </section>

          <section>
            <h2>Evidence sources</h2>

            {data.evidence?.length ? (
              data.evidence.map((item, index) => (
                <article key={index}>
                  <b>{item.type} | {item.source}</b>
                  <pre>
                    {typeof item.content === "string"
                      ? item.content
                      : JSON.stringify(item.content, null, 2)}
                  </pre>
                </article>
              ))
            ) : (
              <p>No evidence items returned.</p>
            )}
          </section>

          {data.sql && (
            <section>
              <h2>PostgreSQL / SQL output</h2>
              <pre>{JSON.stringify(data.sql, null, 2)}</pre>
            </section>
          )}

          {data.analytics && (
            <section>
              <h2>Analytics output</h2>
              <pre>{JSON.stringify(data.analytics, null, 2)}</pre>
            </section>
          )}

          {data.module_errors?.length > 0 && (
            <section>
              <h2>Module warnings</h2>
              {data.module_errors.map((error, index) => (
                <p className="warning" key={index}>{String(error)}</p>
              ))}
            </section>
          )}
        </>
      )}

      <footer>
        Academic project demo | TechNova dataset is synthetic.
      </footer>
    </main>
  );
}
