import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from studyrag_core import PageText, SemanticChunker, SourceDocument


class SemanticChunkerTests(unittest.TestCase):
    def test_preserves_page_heading_and_skips_empty_pages(self) -> None:
        document = SourceDocument(
            id="doc-1",
            course_id="calc",
            filename="notes.txt",
            source_type="txt",
        )
        pages = [
            PageText(text="   ", page_number=1),
            PageText(
                text=(
                    "Related Rates\n"
                    "When variables change together, differentiate both sides with respect to time.\n"
                    "Use the chain rule for each time-varying quantity."
                ),
                page_number=2,
            ),
        ]

        chunks = SemanticChunker(max_tokens=40, overlap_tokens=5).chunk_document(document, pages)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 2)
        self.assertEqual(chunks[0].section_heading, "Related Rates")
        self.assertIn("chain rule", chunks[0].content)

    def test_long_text_uses_token_limit_and_overlap(self) -> None:
        document = SourceDocument(
            id="doc-2",
            course_id="cs",
            filename="recursion.txt",
            source_type="txt",
        )
        text = " ".join(f"term{i}" for i in range(45))
        chunks = SemanticChunker(max_tokens=20, overlap_tokens=5).chunk_document(
            document,
            [PageText(text=text, page_number=1)],
        )

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.token_count <= 20 for chunk in chunks))
        first_tail = chunks[0].content.split()[-5:]
        second_head = chunks[1].content.split()[:5]
        self.assertEqual(first_tail, second_head)


if __name__ == "__main__":
    unittest.main()
