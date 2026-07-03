# StudyRAG Evaluation Results

Generated: 2026-07-02T23:29:55.143598+00:00
Course: StudyRAG Sample Course
Ragas version: 0.4.3
Confidence threshold: 0.2
Top-k: 1

## Summary

| Metric | Value |
|---|---:|
| Total examples | 26 |
| Answerable examples | 22 |
| Refusal examples | 4 |
| Faithfulness | 1.000 |
| Answer relevancy | 0.864 |
| Context precision | 0.955 |
| Context recall | 0.955 |
| Refusal precision | 1.000 |
| Refusal recall | 1.000 |

## Metric Notes

- `faithfulness`: Deterministic local proxy: answer facts must be grounded in retrieved contexts, refusals score when expected.
- `answer_relevancy`: Deterministic local token-F1 against the handwritten reference answer.
- `context_precision`: Ragas ID-based context precision when available, using expected chunk ids from the golden set.
- `context_recall`: Ragas ID-based context recall when available, using expected chunk ids from the golden set.

## Per-Question Results

| ID | Refused | Confidence | Faithfulness | Relevancy | Ctx Precision | Ctx Recall | Retrieved headings |
|---|---:|---:|---:|---:|---:|---:|---|
| rr-01 | false | 0.600 | 1.000 | 0.875 | 1.000 | 1.000 | Related Rates |
| rr-02 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates |
| rr-03 | false | 0.900 | 1.000 | 0.667 | 1.000 | 1.000 | Related Rates |
| rr-04 | false | 0.400 | 1.000 | 0.720 | 1.000 | 1.000 | Related Rates Example |
| rr-05 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates Example |
| rec-01 | false | 1.000 | 1.000 | 0.857 | 1.000 | 1.000 | Recursive Java Methods |
| rec-02 | false | 1.000 | 1.000 | 0.800 | 1.000 | 1.000 | Recursive Java Methods |
| rec-03 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | Recursive Java Methods |
| rec-04 | false | 0.700 | 1.000 | 0.632 | 1.000 | 1.000 | Recursive Java Methods |
| rec-05 | false | 1.000 | 1.000 | 0.923 | 1.000 | 1.000 | Factorial Recursion |
| rec-06 | false | 0.600 | 1.000 | 0.880 | 1.000 | 1.000 | Factorial Recursion |
| newton-01 | false | 0.600 | 1.000 | 0.667 | 1.000 | 1.000 | Newton's Method |
| newton-02 | false | 0.600 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method |
| newton-03 | false | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method |
| newton-04 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method |
| newton-05 | false | 0.400 | 1.000 | 0.842 | 1.000 | 1.000 | Newton's Method Interpretation |
| sql-01 | false | 0.600 | 1.000 | 0.364 | 0.000 | 0.000 | SQL Join Debugging |
| sql-02 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | SQL Joins |
| sql-03 | false | 0.900 | 1.000 | 0.800 | 1.000 | 1.000 | SQL Joins |
| sql-04 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Joins |
| sql-05 | false | 1.000 | 1.000 | 0.903 | 1.000 | 1.000 | SQL Join Debugging |
| sql-06 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Join Debugging |
| refusal-01 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-02 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-03 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-04 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
