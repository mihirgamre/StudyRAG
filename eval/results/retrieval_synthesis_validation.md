# Phase 5.5b Synthesis Validation

Generated: 2026-07-02

Goal: validate that the `top_k=1` precision result from Phase 5.5 was not
overfit to single-chunk golden questions.

Six synthesis questions were added to `eval/golden_dataset.json`, bringing the
dataset to 32 examples:

- 28 answerable questions
- 4 expected refusals
- 6 questions requiring multiple source sections

## Expanded-Set Results

| Setting | Context Precision | Context Recall | Refusal Precision | Refusal Recall | Notes |
|---|---:|---:|---:|---:|---|
| `top_k=1` | 1.000 | 0.911 | 1.000 | 1.000 | Overfit: misses multi-chunk synthesis sources |
| `top_k=2` | 0.571 | 0.982 | 1.000 | 1.000 | Better precision, but misses one synthesis source |
| `top_k=3` | 0.435 | 0.982 | 1.000 | 1.000 | Still misses the same synthesis source |
| `top_k=4` | 0.390 | 1.000 | 1.000 | 1.000 | Current default: preserves synthesis recall |
| `top_k=5` | 0.368 | 1.000 | 1.000 | 1.000 | No recall gain over `top_k=4` |

## Decision

Do not ship `top_k=1`. It produced perfect precision only because the original
golden set was mostly single-chunk answerable.

Use `top_k=4` for now. It lowers context precision from the overfit `1.000` to
`0.390`, but it preserves `1.000` context recall on the expanded synthesis set.
This is the safer default for real student questions that compare, relate, or
synthesize across sections.

Cross-encoder reranking is still a valid next retrieval improvement, but this
pass did not add it because the immediate issue was avoiding silent synthesis
failure before the frontend phase.

Latest checked-in eval output:

- `eval/results/latest.md`
- `eval/results/latest.json`

