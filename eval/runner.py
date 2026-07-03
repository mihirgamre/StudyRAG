from __future__ import annotations

import argparse
import json
import os
import statistics
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from studyrag_core import ConfidenceGate, HashingEmbeddingModel, SemanticChunker, StudyRAGCore
from studyrag_core.text import split_sentences, tokenize
from studyrag_persistence import Base, PostgresHybridRetriever, persist_document_chunks
from studyrag_persistence.database import create_engine_from_url, create_session_factory
from studyrag_persistence.models import ChunkRecord, CourseRecord, DocumentRecord, UserRecord

from .course_material import COURSE_NAME, DOCUMENT_FILENAME, sample_course_pages

EVAL_USER_EMAIL_DOMAIN = "studyrag.local"
DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_GOLDEN_PATH = Path(__file__).resolve().parent / "golden_dataset.json"


@dataclass(frozen=True)
class GoldenExample:
    id: str
    question: str
    reference_answer: str
    expected_source_headings: list[str]
    should_refuse: bool


def run_eval(
    *,
    database_url: str | None = None,
    golden_path: Path = DEFAULT_GOLDEN_PATH,
    output_dir: Path = DEFAULT_RESULTS_DIR,
    confidence_threshold: float = 0.16,
    top_k: int = 4,
) -> dict[str, Any]:
    engine = create_engine_from_url(database_url or _database_url_from_env())
    try:
        _ensure_schema(engine)
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            embedding_model = HashingEmbeddingModel()
            course = seed_eval_course(session, embedding_model)
            examples = load_golden_dataset(golden_path)
            rows = evaluate_examples(
                session,
                course_id=str(course.id),
                examples=examples,
                embedding_model=embedding_model,
                confidence_threshold=confidence_threshold,
                top_k=top_k,
            )

        summary = summarize(rows)
        ragas_summary = compute_ragas_id_context_metrics(rows)
        if ragas_summary:
            summary.update(ragas_summary)
        llm_judge_summary = compute_ragas_llm_judge_metrics(rows)
        if llm_judge_summary:
            summary.update(llm_judge_summary)

        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "course_name": COURSE_NAME,
            "ragas_version": _ragas_version(),
            "confidence_threshold": confidence_threshold,
            "top_k": top_k,
            "metric_notes": {
                "faithfulness": (
                    "Ragas LLM-as-judge faithfulness using the configured evaluator model."
                    if llm_judge_summary
                    else "Deterministic local proxy: answer facts must be grounded in retrieved contexts, refusals score when expected."
                ),
                "answer_relevancy": (
                    "Ragas LLM-as-judge answer relevancy using the configured evaluator model."
                    if llm_judge_summary
                    else "Deterministic local token-F1 against the handwritten reference answer."
                ),
                "context_precision": "Ragas ID-based context precision when available, using expected chunk ids from the golden set.",
                "context_recall": "Ragas ID-based context recall when available, using expected chunk ids from the golden set.",
            },
            "summary": summary,
            "rows": rows,
        }
        write_results(result, output_dir)
        return result
    finally:
        engine.dispose()


def seed_eval_course(session: Session, embedding_model: HashingEmbeddingModel) -> CourseRecord:
    user = UserRecord(email=f"eval-{uuid.uuid4()}@{EVAL_USER_EMAIL_DOMAIN}", hashed_password="eval-only")
    course = CourseRecord(user=user, name=COURSE_NAME)
    document = DocumentRecord(
        course=course,
        filename=DOCUMENT_FILENAME,
        source_type="txt",
        storage_url="local://eval/study-rag-sample-course-notes.txt",
        status="pending",
    )
    session.add_all([user, course, document])
    session.flush()
    persist_document_chunks(
        session,
        document=document,
        pages=sample_course_pages(),
        chunker=SemanticChunker(max_tokens=80, overlap_tokens=8),
        embedding_model=embedding_model,
    )
    session.commit()
    return course


def load_golden_dataset(path: Path = DEFAULT_GOLDEN_PATH) -> list[GoldenExample]:
    raw_examples = json.loads(path.read_text(encoding="utf-8"))
    return [GoldenExample(**example) for example in raw_examples]


def evaluate_examples(
    session: Session,
    *,
    course_id: str,
    examples: list[GoldenExample],
    embedding_model: HashingEmbeddingModel,
    confidence_threshold: float,
    top_k: int,
) -> list[dict[str, Any]]:
    retriever = PostgresHybridRetriever(session, embedding_model)
    core = StudyRAGCore(
        retriever,
        confidence_gate=ConfidenceGate(min_similarity=confidence_threshold),
    )
    expected_chunks_by_heading = _expected_chunks_by_heading(session, uuid.UUID(course_id))
    rows: list[dict[str, Any]] = []

    for example in examples:
        hits = retriever.retrieve(course_id, example.question, top_k=top_k)
        response = core.prepare_generation(course_id=course_id, question=example.question, top_k=top_k)
        retrieved_ids = [hit.chunk.id for hit in hits]
        retrieved_contexts = [hit.chunk.content for hit in hits]
        expected_ids = [
            str(chunk.id)
            for heading in example.expected_source_headings
            for chunk in expected_chunks_by_heading.get(heading, [])
        ]
        faithfulness = score_faithfulness(response.answer, [hit.chunk.content for hit in hits], response.refused, example)
        relevancy = score_answer_relevancy(response.answer, example.reference_answer, response.refused, example)
        local_context_precision = score_context_precision(retrieved_ids, expected_ids)
        local_context_recall = score_context_recall(retrieved_ids, expected_ids, example.should_refuse)

        rows.append(
            {
                "id": example.id,
                "question": example.question,
                "reference_answer": example.reference_answer,
                "answer": response.answer,
                "should_refuse": example.should_refuse,
                "refused": response.refused,
                "confidence": response.confidence,
                "expected_source_headings": example.expected_source_headings,
                "retrieved_headings": [hit.chunk.section_heading for hit in hits],
                "retrieved_contexts": retrieved_contexts,
                "retrieved_context_ids": retrieved_ids,
                "reference_context_ids": expected_ids,
                "faithfulness": faithfulness,
                "answer_relevancy": relevancy,
                "context_precision": local_context_precision,
                "context_recall": local_context_recall,
            }
        )

    return rows


def score_faithfulness(answer: str, contexts: list[str], refused: bool, example: GoldenExample) -> float:
    if refused:
        return 1.0 if example.should_refuse else 0.0
    context_tokens = set(tokenize(" ".join(contexts), keep_stop_words=False))
    answer_tokens = set(tokenize(_strip_citations(answer), keep_stop_words=False))
    if not answer_tokens:
        return 0.0
    return len(answer_tokens & context_tokens) / len(answer_tokens)


def score_answer_relevancy(answer: str, reference_answer: str, refused: bool, example: GoldenExample) -> float:
    if example.should_refuse:
        return 1.0 if refused else 0.0
    if refused:
        return 0.0
    stripped = _strip_citations(answer)
    candidates = split_sentences(stripped) or [stripped]
    return max(token_f1(candidate, reference_answer) for candidate in candidates)


def score_context_precision(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    if not retrieved_ids:
        return 0.0
    if not expected_ids:
        return 1.0

    expected = set(expected_ids)
    precisions_at_relevant: list[float] = []
    relevant_seen = 0
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in expected:
            relevant_seen += 1
            precisions_at_relevant.append(relevant_seen / rank)
    if not precisions_at_relevant:
        return 0.0
    return statistics.mean(precisions_at_relevant)


def score_context_recall(retrieved_ids: list[str], expected_ids: list[str], should_refuse: bool) -> float:
    if should_refuse:
        return 1.0
    if not expected_ids:
        return 0.0
    return len(set(retrieved_ids) & set(expected_ids)) / len(set(expected_ids))


def token_f1(answer: str, reference: str) -> float:
    answer_tokens = tokenize(answer, keep_stop_words=False)
    reference_tokens = tokenize(reference, keep_stop_words=False)
    if not answer_tokens or not reference_tokens:
        return 0.0
    answer_counts = _counts(answer_tokens)
    reference_counts = _counts(reference_tokens)
    overlap = sum(min(answer_counts.get(token, 0), reference_counts.get(token, 0)) for token in answer_counts)
    if overlap == 0:
        return 0.0
    precision = overlap / len(answer_tokens)
    recall = overlap / len(reference_tokens)
    return 2 * precision * recall / (precision + recall)


def compute_ragas_id_context_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import _IDBasedContextPrecision, _IDBasedContextRecall
    except Exception:
        return {}

    dataset = Dataset.from_list(
        [
            {
                "retrieved_context_ids": row["retrieved_context_ids"],
                "reference_context_ids": row["reference_context_ids"],
            }
            for row in rows
            if not row["should_refuse"]
        ]
    )
    if len(dataset) == 0:
        return {}

    result = evaluate(
        dataset,
        metrics=[_IDBasedContextPrecision(), _IDBasedContextRecall()],
        show_progress=False,
        raise_exceptions=False,
    )
    as_dict = {
        key: _mean(score[key] for score in result.scores if key in score)
        for key in ("id_based_context_precision", "id_based_context_recall")
    }
    updates: dict[str, float] = {}
    if "id_based_context_precision" in as_dict:
        updates["context_precision"] = float(as_dict["id_based_context_precision"])
    if "id_based_context_recall" in as_dict:
        updates["context_recall"] = float(as_dict["id_based_context_recall"])
    return updates


def compute_ragas_llm_judge_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    api_key = os.getenv("RAGAS_EVALUATOR_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("RAGAS_EVALUATOR_MODEL")
    if not api_key:
        return {}
    if not model:
        raise RuntimeError("RAGAS_EVALUATOR_MODEL is required when RAGAS_EVALUATOR_API_KEY is set")

    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import AnswerRelevancy, Faithfulness
    except Exception as exc:
        raise RuntimeError(
            "Ragas LLM judge metrics require ragas and langchain-openai. Install with: pip install -e '.[eval]'"
        ) from exc

    base_url = os.getenv("RAGAS_EVALUATOR_BASE_URL") or os.getenv("LLM_BASE_URL") or None
    embeddings_model = os.getenv("RAGAS_EVALUATOR_EMBEDDING_MODEL", "text-embedding-3-small")
    llm = LangchainLLMWrapper(
        ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0,
        )
    )
    embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=embeddings_model,
        )
    )
    dataset = Dataset.from_list(
        [
            {
                "user_input": row["question"],
                "response": row["answer"],
                "retrieved_contexts": row["retrieved_contexts"],
            }
            for row in rows
        ]
    )
    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
        ],
        show_progress=False,
        raise_exceptions=False,
    )
    return {
        key: _mean(score[key] for score in result.scores if key in score)
        for key in ("faithfulness", "answer_relevancy")
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    expected_refusals = [row for row in rows if row["should_refuse"]]
    predicted_refusals = [row for row in rows if row["refused"]]
    true_refusals = [row for row in rows if row["should_refuse"] and row["refused"]]

    return {
        "total_examples": len(rows),
        "answerable_examples": len([row for row in rows if not row["should_refuse"]]),
        "refusal_examples": len(expected_refusals),
        "faithfulness": _mean(row["faithfulness"] for row in rows),
        "answer_relevancy": _mean(row["answer_relevancy"] for row in rows),
        "context_precision": _mean(row["context_precision"] for row in rows if not row["should_refuse"]),
        "context_recall": _mean(row["context_recall"] for row in rows if not row["should_refuse"]),
        "refusal_precision": len(true_refusals) / len(predicted_refusals) if predicted_refusals else 0.0,
        "refusal_recall": len(true_refusals) / len(expected_refusals) if expected_refusals else 0.0,
    }


def write_results(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output_dir / "latest.md").write_text(render_markdown(result), encoding="utf-8")


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# StudyRAG Evaluation Results",
        "",
        f"Generated: {result['generated_at']}",
        f"Course: {result['course_name']}",
        f"Ragas version: {result['ragas_version']}",
        f"Confidence threshold: {result['confidence_threshold']}",
        f"Top-k: {result['top_k']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total examples | {summary['total_examples']} |",
        f"| Answerable examples | {summary['answerable_examples']} |",
        f"| Refusal examples | {summary['refusal_examples']} |",
        f"| Faithfulness | {summary['faithfulness']:.3f} |",
        f"| Answer relevancy | {summary['answer_relevancy']:.3f} |",
        f"| Context precision | {summary['context_precision']:.3f} |",
        f"| Context recall | {summary['context_recall']:.3f} |",
        f"| Refusal precision | {summary['refusal_precision']:.3f} |",
        f"| Refusal recall | {summary['refusal_recall']:.3f} |",
        "",
        "## Metric Notes",
        "",
    ]
    for name, note in result["metric_notes"].items():
        lines.append(f"- `{name}`: {note}")

    lines.extend(
        [
            "",
            "## Per-Question Results",
            "",
            "| ID | Refused | Confidence | Faithfulness | Relevancy | Ctx Precision | Ctx Recall | Retrieved headings |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in result["rows"]:
        headings = ", ".join(str(item) for item in row["retrieved_headings"])
        lines.append(
            "| {id} | {refused} | {confidence:.3f} | {faithfulness:.3f} | {answer_relevancy:.3f} | "
            "{context_precision:.3f} | {context_recall:.3f} | {headings} |".format(
                id=row["id"],
                refused=str(row["refused"]).lower(),
                confidence=row["confidence"],
                faithfulness=row["faithfulness"],
                answer_relevancy=row["answer_relevancy"],
                context_precision=row["context_precision"],
                context_recall=row["context_recall"],
                headings=headings,
            )
        )
    lines.append("")
    return "\n".join(lines)


def _expected_chunks_by_heading(session: Session, course_id: uuid.UUID) -> dict[str, list[ChunkRecord]]:
    chunks = session.scalars(
        select(ChunkRecord)
        .join(ChunkRecord.document)
        .where(DocumentRecord.course_id == course_id)
        .order_by(ChunkRecord.chunk_index)
    ).all()
    by_heading: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        if chunk.section_heading:
            by_heading.setdefault(chunk.section_heading, []).append(chunk)
    return by_heading


def _ensure_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


def _database_url_from_env() -> str:
    url = os.getenv("STUDYRAG_EVAL_DATABASE_URL") or os.getenv("STUDYRAG_TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set STUDYRAG_EVAL_DATABASE_URL, STUDYRAG_TEST_DATABASE_URL, or DATABASE_URL")
    return url


def _strip_citations(answer: str) -> str:
    return answer.replace("[source 1]", "").replace("[source 2]", "").replace("[source 3]", "").replace("[source 4]", "")


def _counts(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def _mean(values) -> float:
    materialized = list(values)
    if not materialized:
        return 0.0
    return float(statistics.mean(materialized))


def _ragas_version() -> str:
    try:
        import ragas

        return str(ragas.__version__)
    except Exception:
        return "not available"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run StudyRAG retrieval/generation evaluation.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--golden-path", type=Path, default=DEFAULT_GOLDEN_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--confidence-threshold", type=float, default=0.16)
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    result = run_eval(
        database_url=args.database_url,
        golden_path=args.golden_path,
        output_dir=args.output_dir,
        confidence_threshold=args.confidence_threshold,
        top_k=args.top_k,
    )
    summary = result["summary"]
    print(
        "faithfulness={faithfulness:.3f} answer_relevancy={answer_relevancy:.3f} "
        "context_precision={context_precision:.3f} context_recall={context_recall:.3f} "
        "refusal_precision={refusal_precision:.3f} refusal_recall={refusal_recall:.3f}".format(**summary)
    )


if __name__ == "__main__":
    main()
