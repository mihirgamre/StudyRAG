import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from studyrag_core import (
    ConfidenceGate,
    HashingEmbeddingModel,
    InMemoryHybridRetriever,
    Message,
    PageText,
    PromptBuilder,
    SemanticChunker,
    SourceDocument,
    StudyRAGCore,
)


def build_chunks():
    chunker = SemanticChunker(max_tokens=80, overlap_tokens=10)
    calc_doc = SourceDocument("calc-doc", "calc", "calculus-notes.txt", "txt")
    cs_doc = SourceDocument("cs-doc", "cs", "java-notes.txt", "txt")
    other_calc_doc = SourceDocument("other-calc", "other-calc", "other.txt", "txt")

    return (
        chunker.chunk_document(
            calc_doc,
            [
                PageText(
                    page_number=12,
                    text=(
                        "Related Rates\n"
                        "Related rates problems connect quantities that change with time. "
                        "Differentiate the equation with respect to time and solve for the unknown rate."
                    ),
                )
            ],
        )
        + chunker.chunk_document(
            cs_doc,
            [
                PageText(
                    page_number=3,
                    text=(
                        "Recursion\n"
                        "A recursive Java method calls itself and must include a base case."
                    ),
                )
            ],
        )
        + chunker.chunk_document(
            other_calc_doc,
            [
                PageText(
                    page_number=5,
                    text=(
                        "Related Rates\n"
                        "This other course should never be returned for the calc course."
                    ),
                )
            ],
        )
    )


class RetrievalAndRagTests(unittest.TestCase):
    def test_retrieval_is_course_scoped_and_hybrid(self) -> None:
        retriever = InMemoryHybridRetriever(HashingEmbeddingModel(dimensions=128))
        retriever.index_chunks(build_chunks())

        hits = retriever.retrieve(
            "calc",
            "How do related rates problems use time derivatives?",
            top_k=3,
        )

        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].chunk.course_id, "calc")
        self.assertEqual(hits[0].chunk.filename, "calculus-notes.txt")
        self.assertGreater(hits[0].keyword_score, 0.0)
        self.assertNotEqual(hits[0].chunk.document_id, "other-calc")

    def test_confidence_gate_refuses_low_similarity_without_citations(self) -> None:
        retriever = InMemoryHybridRetriever(HashingEmbeddingModel(dimensions=128))
        retriever.index_chunks(build_chunks())
        core = StudyRAGCore(
            retriever,
            confidence_gate=ConfidenceGate(min_similarity=0.55),
        )

        response = core.prepare_generation(
            course_id="calc",
            question="What does the syllabus say about grading late homework?",
        )

        self.assertTrue(response.refused)
        self.assertEqual(response.citations, [])
        self.assertIn("don't have enough information", response.answer)

    def test_supported_answer_maps_source_tags_to_structured_citations(self) -> None:
        retriever = InMemoryHybridRetriever(HashingEmbeddingModel(dimensions=128))
        retriever.index_chunks(build_chunks())
        core = StudyRAGCore(
            retriever,
            confidence_gate=ConfidenceGate(min_similarity=0.05),
        )

        response = core.prepare_generation(
            course_id="calc",
            question="How do I solve related rates problems?",
        )

        self.assertFalse(response.refused)
        self.assertGreaterEqual(len(response.citations), 1)
        citation = response.citations[0]
        self.assertEqual(citation.filename, "calculus-notes.txt")
        self.assertEqual(citation.page_number, 12)
        self.assertIn("Related rates", citation.snippet)
        self.assertIn("[source 1]", response.answer)

    def test_long_history_is_trimmed_without_error(self) -> None:
        builder = PromptBuilder(max_history_tokens=12, max_context_tokens=100)
        retriever = InMemoryHybridRetriever(HashingEmbeddingModel(dimensions=128))
        retriever.index_chunks(build_chunks())
        hits = retriever.retrieve("calc", "related rates", top_k=1)

        request = builder.build(
            question="Can you explain it again?",
            hits=hits,
            confidence=hits[0].vector_score,
            history=[
                Message(role="user", content=" ".join(f"old{i}" for i in range(100))),
                Message(role="assistant", content="recent explanation about related rates"),
            ],
        )

        self.assertEqual(len(request.included_history), 1)
        self.assertEqual(request.included_history[0].role, "assistant")
        self.assertIn("recent explanation", request.prompt)
        self.assertIn("Reference data:", request.prompt)


if __name__ == "__main__":
    unittest.main()
