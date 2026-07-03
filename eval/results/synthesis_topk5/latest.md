# StudyRAG Evaluation Results

Generated: 2026-07-02T23:37:24.313801+00:00
Course: StudyRAG Sample Course
Ragas version: 0.4.3
Confidence threshold: 0.2
Top-k: 5

## Summary

| Metric | Value |
|---|---:|
| Total examples | 32 |
| Answerable examples | 28 |
| Refusal examples | 4 |
| Faithfulness | 0.625 |
| Answer relevancy | 0.551 |
| Context precision | nan |
| Context recall | 0.571 |
| Refusal precision | 0.250 |
| Refusal recall | 1.000 |

## Metric Notes

- `faithfulness`: Deterministic local proxy: answer facts must be grounded in retrieved contexts, refusals score when expected.
- `answer_relevancy`: Deterministic local token-F1 against the handwritten reference answer.
- `context_precision`: Ragas ID-based context precision when available, using expected chunk ids from the golden set.
- `context_recall`: Ragas ID-based context recall when available, using expected chunk ids from the golden set.

## Per-Question Results

| ID | Refused | Confidence | Faithfulness | Relevancy | Ctx Precision | Ctx Recall | Retrieved headings |
|---|---:|---:|---:|---:|---:|---:|---|
| rr-01 | false | 0.600 | 1.000 | 0.875 | 1.000 | 1.000 | Related Rates, Related Rates Example, Recursive Java Methods |
| rr-02 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates, Related Rates Example |
| rr-03 | false | 0.900 | 1.000 | 0.667 | 1.000 | 1.000 | Related Rates, Related Rates Example, Recursive Java Methods, Newton's Method |
| rr-04 | false | 0.400 | 1.000 | 0.720 | 1.000 | 1.000 | Related Rates Example, Related Rates |
| rr-05 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates Example, SQL Join Debugging |
| rec-01 | false | 1.000 | 1.000 | 0.857 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method Interpretation, Newton's Method |
| rec-02 | false | 1.000 | 1.000 | 0.800 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method, SQL Joins, Newton's Method Interpretation |
| rec-03 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Related Rates, Newton's Method |
| rec-04 | false | 0.700 | 1.000 | 0.632 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method Interpretation |
| rec-05 | false | 1.000 | 1.000 | 0.923 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods, SQL Join Debugging, Related Rates Example, Related Rates |
| rec-06 | false | 0.600 | 1.000 | 0.880 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods, Related Rates |
| newton-01 | false | 0.600 | 1.000 | 0.667 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion |
| newton-02 | false | 0.600 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion |
| newton-03 | false | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Recursive Java Methods, Newton's Method Interpretation, Factorial Recursion |
| newton-04 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion, Related Rates Example |
| newton-05 | false | 0.258 | 1.000 | 0.842 | 1.000 | 1.000 | Newton's Method Interpretation, Related Rates Example, Newton's Method, Factorial Recursion, Related Rates |
| sql-01 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| sql-02 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| sql-03 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| sql-04 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| sql-05 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| sql-06 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| refusal-01 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-02 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-03 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-04 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| synth-01 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| synth-02 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| synth-03 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| synth-04 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| synth-05 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| synth-06 | true | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
