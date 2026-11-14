# Research Results Summary

The evaluation used the synthetic TechNova documents and PostgreSQL dataset
included with this project. Five live FastAPI end-to-end queries were executed:
document-only, SQL-only, analytics-only, hybrid, and full-hybrid. All five
returned HTTP 200, selected the expected route, executed the required modules,
returned evidence, and completed without module errors. Route correctness,
module execution, and evidence presence passed separately for all five. The
functional answer-assertion pass count was **5/5** after enforcing structured
analytics facts for monthly extrema. The PostgreSQL minimum is April, not
October.

Document retrieval over five labelled queries measured Precision@5 **0.20**,
Recall@5 **1.00**, and MRR **1.00**. The relevant document was ranked first in
each case, but the single relevant-document-per-query setup means four of the
five returned items were non-relevant at k=5. Mean measured retrieval latency
was **2.0802 seconds** in the final run, including a measured cold-start
latency of **10.2288 seconds**. The four subsequent warm retrievals averaged
**0.0430 seconds**. The first query was retained and explicitly labelled
cold-start.

The controlled text-to-SQL set achieved **4/4 (1.00) accuracy** for customer,
employee, product, and delivered-revenue questions. SQL validation checks
rejected all three unsafe/invalid examples, and no controlled SQL execution
failed. Analytics monthly revenue, city revenue, and two-standard-deviation
anomaly outputs all matched independently calculated PostgreSQL results.

Evidence verification passed the supported, unsupported, and
insufficient-evidence cases (**3/3 functional verifier unit tests**). This is
not semantic factual verification: numeric checks look for matching numbers in
serialized evidence and document checks use lexical overlap, not semantic
entailment. Semantic faithfulness and hallucination detection were not
performed. Mixed answers can therefore be marked `review_required`, and a
`supported` status is not a proof of truthfulness.

The analytics module independently matched every monthly PostgreSQL revenue
figure, the maximum (May 2026, 1,569,800), and the minimum (April 2026,
546,000). October was verified as 583,200, not the minimum.

Measured route latencies were: documents **1.0041 s**, SQL **2.1206 s**,
analytics **9.5473 s**, hybrid **12.2330 s**, and full-hybrid **25.9462 s**.
These are live-service measurements, not controlled performance benchmarks;
the document route included model-loading variability. Forecast values remain
experimental linear-trend estimates and are not validated business forecasts.
All records and documents are synthetic and should not be interpreted as real
enterprise evidence.
