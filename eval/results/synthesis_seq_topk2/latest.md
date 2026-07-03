# StudyRAG Evaluation Results

Generated: 2026-07-02T23:38:26.220089+00:00
Course: StudyRAG Sample Course
Ragas version: 0.4.3
Confidence threshold: 0.2
Top-k: 2

## Summary

| Metric | Value |
|---|---:|
| Total examples | 32 |
| Answerable examples | 28 |
| Refusal examples | 4 |
| Faithfulness | 1.000 |
| Answer relevancy | 0.766 |
| Context precision | 0.571 |
| Context recall | 0.982 |
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
| rr-01 | false | 0.600 | 1.000 | 0.875 | 1.000 | 1.000 | Related Rates, Related Rates Example |
| rr-02 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates, Related Rates Example |
| rr-03 | false | 0.900 | 1.000 | 0.667 | 1.000 | 1.000 | Related Rates, Related Rates Example |
| rr-04 | false | 0.400 | 1.000 | 0.720 | 1.000 | 1.000 | Related Rates Example, Related Rates |
| rr-05 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates Example, SQL Join Debugging |
| rec-01 | false | 1.000 | 1.000 | 0.857 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion |
| rec-02 | false | 1.000 | 1.000 | 0.800 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion |
| rec-03 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion |
| rec-04 | false | 0.700 | 1.000 | 0.632 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion |
| rec-05 | false | 1.000 | 1.000 | 0.923 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods |
| rec-06 | false | 0.600 | 1.000 | 0.308 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods |
| newton-01 | false | 0.600 | 1.000 | 0.667 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation |
| newton-02 | false | 0.600 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation |
| newton-03 | false | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Recursive Java Methods |
| newton-04 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation |
| newton-05 | false | 0.400 | 1.000 | 0.842 | 1.000 | 1.000 | Newton's Method Interpretation, Related Rates Example |
| sql-01 | false | 0.800 | 1.000 | 0.917 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-02 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-03 | false | 0.900 | 1.000 | 0.800 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-04 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-05 | false | 1.000 | 1.000 | 0.903 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins |
| sql-06 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins |
| refusal-01 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-02 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-03 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-04 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| synth-01 | false | 0.500 | 1.000 | 0.148 | 1.000 | 0.500 | Related Rates, Recursive Java Methods |
| synth-02 | false | 0.900 | 1.000 | 0.500 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion |
| synth-03 | false | 0.900 | 1.000 | 0.303 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| synth-04 | false | 1.000 | 1.000 | 0.595 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins |
| synth-05 | false | 1.000 | 1.000 | 0.410 | 1.000 | 1.000 | Related Rates, Newton's Method |
| synth-06 | false | 0.500 | 1.000 | 0.118 | 1.000 | 1.000 | Newton's Method, Recursive Java Methods |
