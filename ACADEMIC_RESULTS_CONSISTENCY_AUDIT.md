# Academic Results Consistency Audit

Date: 2026-11-11

## Purpose

This audit compares the latest executable validation artifacts with the
attached IEEE-style paper and the existing project-report PDF. It does not
replace either source document and does not change measured experimental
results.

## Canonical verified results

The current canonical record is
[RESEARCH_VALIDATION_REPORT.md](./RESEARCH_VALIDATION_REPORT.md), supported by
the CSV artifacts and the final validation run:

| Area | Verified result |
|---|---|
| RAG benchmark | 10 questions; Precision@5 0.2000; returned-document precision 0.8333; Recall@5 1.0000; MRR 1.0000 |
| Controlled Text-to-SQL | 10/10 correct |
| SQL safety | 8/8 unsafe probes rejected |
| Analytics | 6/6 validation checks passed |
| API routing | 7/7 routes passed in a fresh API process |
| Regression suite | 28 tests passed |
| Database | 297 existing records unchanged |
| Forecasting | Experimental and unvalidated; no forecast accuracy claimed |

Precision@5 uses a fixed denominator of five. Returned-document precision
uses the number of documents actually returned. Recall@5 and MRR are separate
metrics. These are controlled prototype results, not general model accuracy
estimates.

## Attached IEEE-style paper

The attached IEEE-style paper is consistent with the canonical results in its
abstract and evaluation sections: it reports the ten-query RAG benchmark,
10/10 SQL, 8/8 safety, 6 analytics checks, 7/7 routes, and 28 regression
tests. It also correctly describes heuristic verification and experimental
forecasting limitations.

Before submission, retain the explicit wording that revenue values are
**revenue units** because the synthetic dataset defines no currency
denomination.

## Existing project-report PDF

The existing project-report PDF contains an older historical result block that
reports:

- a five-query retrieval evaluation;
- 4/4 controlled Text-to-SQL cases;
- 20 regression tests; and
- five API route tests.

That block must not be presented as the latest evaluation. It should either be
labelled as an earlier baseline or replaced in the editable source before a
final PDF is submitted. The newer chapter sections should use the canonical
values above and retain their limitations.

## Source and formatting note

The attached file named `IEEE_Conference_Template__1_ (2).pdf` is an
IEEE-style conference paper, not evidence of GGSIPU dissertation formatting.
It can guide paper structure and citation style, but the dissertation should
also be checked against the institution's current official rules for page
length, front matter, declarations, certificates, and binding format.

## Recommended document workflow

1. Treat the current validation report and CSV files as the results source of
   truth.
2. Update the editable project-report source to remove or label the stale
   historical result block.
3. Keep the IEEE paper's measured values unchanged.
4. Add diagrams and screenshots only when they are taken from the actual
   implementation; use labelled placeholders when evidence is unavailable.
5. Do not claim semantic entailment, forecast accuracy, browser automation,
   production security, or general-domain accuracy.

No PostgreSQL schema, data, original document, or ChromaDB record was modified
by this audit.
