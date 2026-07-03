# StudyRAG Evaluation Results

Generated: 2026-07-02T23:39:45.941267+00:00
Course: StudyRAG Sample Course
Ragas version: 0.4.3
Confidence threshold: 0.2
Top-k: 4

## Summary

| Metric | Value |
|---|---:|
| Total examples | 32 |
| Answerable examples | 28 |
| Refusal examples | 4 |
| Faithfulness | 1.000 |
| Answer relevancy | 0.777 |
| Context precision | 0.390 |
| Context recall | 1.000 |
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
| rr-01 | false | 0.600 | 1.000 | 0.875 | 1.000 | 1.000 | Related Rates, Related Rates Example, Recursive Java Methods |
| rr-02 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates, Related Rates Example |
| rr-03 | false | 0.900 | 1.000 | 0.667 | 1.000 | 1.000 | Related Rates, Related Rates Example, Recursive Java Methods, Newton's Method |
| rr-04 | false | 0.400 | 1.000 | 0.720 | 1.000 | 1.000 | Related Rates Example, Related Rates |
| rr-05 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | Related Rates Example, SQL Join Debugging |
| rec-01 | false | 1.000 | 1.000 | 0.857 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method Interpretation, Newton's Method |
| rec-02 | false | 1.000 | 1.000 | 0.800 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method, SQL Joins |
| rec-03 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Related Rates, Newton's Method |
| rec-04 | false | 0.700 | 1.000 | 0.632 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Newton's Method Interpretation |
| rec-05 | false | 1.000 | 1.000 | 0.923 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods, SQL Join Debugging, Related Rates Example |
| rec-06 | false | 0.600 | 1.000 | 0.880 | 1.000 | 1.000 | Factorial Recursion, Recursive Java Methods, Related Rates |
| newton-01 | false | 0.600 | 1.000 | 0.667 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion |
| newton-02 | false | 0.600 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion |
| newton-03 | false | 0.500 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Recursive Java Methods, Newton's Method Interpretation, Factorial Recursion |
| newton-04 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | Newton's Method, Newton's Method Interpretation, Recursive Java Methods, Factorial Recursion |
| newton-05 | false | 0.400 | 1.000 | 0.842 | 1.000 | 1.000 | Newton's Method Interpretation, Related Rates Example, Newton's Method, Factorial Recursion |
| sql-01 | false | 0.800 | 1.000 | 0.917 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging, Factorial Recursion, Recursive Java Methods |
| sql-02 | false | 1.000 | 1.000 | 0.762 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-03 | false | 0.900 | 1.000 | 0.800 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging, Newton's Method Interpretation |
| sql-04 | false | 0.400 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| sql-05 | false | 1.000 | 1.000 | 0.903 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins, Recursive Java Methods |
| sql-06 | false | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins |
| refusal-01 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-02 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-03 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| refusal-04 | true | 0.000 | 1.000 | 1.000 | 0.000 | 1.000 |  |
| synth-01 | false | 0.500 | 1.000 | 0.148 | 0.750 | 1.000 | Related Rates, Recursive Java Methods, Newton's Method Interpretation, Newton's Method |
| synth-02 | false | 0.900 | 1.000 | 0.500 | 1.000 | 1.000 | Recursive Java Methods, Factorial Recursion, Related Rates, Newton's Method |
| synth-03 | false | 0.900 | 1.000 | 0.303 | 1.000 | 1.000 | SQL Joins, SQL Join Debugging |
| synth-04 | false | 1.000 | 1.000 | 0.595 | 1.000 | 1.000 | SQL Join Debugging, SQL Joins |
| synth-05 | false | 1.000 | 1.000 | 0.182 | 1.000 | 1.000 | Related Rates, Newton's Method, Newton's Method Interpretation, Related Rates Example |
| synth-06 | false | 0.500 | 1.000 | 0.125 | 1.000 | 1.000 | Newton's Method, Recursive Java Methods, Newton's Method Interpretation, Factorial Recursion |
