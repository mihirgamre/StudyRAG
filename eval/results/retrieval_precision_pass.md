# Phase 5.5 Retrieval Precision Pass

Generated: 2026-07-02

Superseded note: Phase 5.5b added multi-chunk synthesis questions and showed
that `top_k=1` was overfit to single-chunk questions. See
`eval/results/retrieval_synthesis_validation.md` for the current default
decision.

Goal: improve ID-based context precision before building the frontend citation UI.

The Phase 5 baseline had perfect recall but weak precision:

| Setting | Change | Context Precision | Context Recall |
|---|---|---:|---:|
| `top_k=5` | Phase 5 baseline | 0.328 | 1.000 |
| `top_k=3` | Reduced k only | 0.379 | 1.000 |
| `top_k=2` | Reduced k only | 0.500 | 1.000 |
| `top_k=1` | Reduced k only | 0.955 | 0.955 |
| `top_k=1` + tie-break | Prefer higher full-text score on RRF ties | 1.000 | 1.000 |

The only `top_k=1` miss before the tie-break was:

- Question: "What does an inner join return?"
- Expected chunk: `SQL Joins`
- Retrieved chunk: `SQL Join Debugging`

Both chunks matched `inner join`, and reciprocal-rank fusion tied because one had vector rank 1 / keyword rank 2 while the other had vector rank 2 / keyword rank 1. The final fix keeps the same hybrid retrieval but sorts ties by `(fused_score, keyword_score, vector_score)`, which correctly prefers the chunk with the stronger full-text match for this query.

Cross-encoder reranking was not added in this pass because the cheaper fix reached `1.000` context precision and `1.000` context recall on the 26-question golden set.

Latest checked-in eval output:

- `eval/results/latest.md`
- `eval/results/latest.json`
