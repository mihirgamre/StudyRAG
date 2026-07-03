import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TEST_DATABASE_URL = os.getenv("STUDYRAG_TEST_DATABASE_URL")

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from studyrag_core import HashingEmbeddingModel, PageText
    from studyrag_persistence import Base, PostgresHybridRetriever, persist_document_chunks
    from studyrag_persistence.database import normalize_database_url
    from studyrag_persistence.models import CourseRecord, DocumentRecord, UserRecord

    IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - exercised only without optional db deps.
    IMPORT_ERROR = exc


@unittest.skipUnless(TEST_DATABASE_URL, "set STUDYRAG_TEST_DATABASE_URL to run Postgres integration tests")
@unittest.skipIf(IMPORT_ERROR is not None, f"database dependencies are not installed: {IMPORT_ERROR}")
class PostgresPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(TEST_DATABASE_URL, future=True)
        with cls.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(cls.engine)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_chunk_embed_store_retrieve_round_trip_is_course_scoped(self) -> None:
        embedding_model = HashingEmbeddingModel()

        with self.Session() as session:
            user = UserRecord(email="student@example.com", hashed_password="not-real")
            calc = CourseRecord(user=user, name="Calculus II")
            cs = CourseRecord(user=user, name="Intro Java")
            calc_doc = DocumentRecord(
                course=calc,
                filename="calculus-notes.txt",
                source_type="txt",
                storage_url="s3://bucket/calculus-notes.txt",
            )
            cs_doc = DocumentRecord(
                course=cs,
                filename="java-notes.txt",
                source_type="txt",
                storage_url="s3://bucket/java-notes.txt",
            )
            session.add_all([user, calc, cs, calc_doc, cs_doc])
            session.flush()

            persist_document_chunks(
                session,
                document=calc_doc,
                pages=[
                    PageText(
                        text=(
                            "Related Rates\n"
                            "Related rates problems connect changing quantities over time. "
                            "Differentiate with respect to time and solve for the requested rate."
                        ),
                        page_number=12,
                    )
                ],
                embedding_model=embedding_model,
            )
            persist_document_chunks(
                session,
                document=cs_doc,
                pages=[
                    PageText(
                        text="Recursion\nA recursive Java method calls itself and includes a base case.",
                        page_number=3,
                    )
                ],
                embedding_model=embedding_model,
            )
            session.commit()

            retriever = PostgresHybridRetriever(session, embedding_model)
            hits = retriever.retrieve(str(calc.id), "How do related rates use time?", top_k=3)

            self.assertGreaterEqual(len(hits), 1)
            self.assertEqual(hits[0].chunk.course_id, str(calc.id))
            self.assertEqual(hits[0].chunk.filename, "calculus-notes.txt")
            self.assertEqual(hits[0].chunk.page_number, 12)
            self.assertGreater(hits[0].vector_score, 0.0)
            self.assertGreater(hits[0].keyword_score, 0.0)
            self.assertTrue(all(hit.chunk.course_id == str(calc.id) for hit in hits))

            cs_hits = retriever.retrieve(str(cs.id), "How does Java recursion use a base case?", top_k=3)

            self.assertGreaterEqual(len(cs_hits), 1)
            self.assertEqual(cs_hits[0].chunk.course_id, str(cs.id))
            self.assertEqual(cs_hits[0].chunk.filename, "java-notes.txt")
            self.assertGreater(cs_hits[0].vector_score, 0.0)
            self.assertGreater(cs_hits[0].keyword_score, 0.0)
            self.assertTrue(all(hit.chunk.course_id == str(cs.id) for hit in cs_hits))


class DatabaseUrlTests(unittest.TestCase):
    def test_normalizes_platform_postgres_urls_to_installed_psycopg_driver(self) -> None:
        self.assertEqual(
            normalize_database_url("postgres://user:pass@host/db?sslmode=require"),
            "postgresql+psycopg://user:pass@host/db?sslmode=require",
        )
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@host/db?sslmode=require"),
            "postgresql+psycopg://user:pass@host/db?sslmode=require",
        )
        self.assertEqual(
            normalize_database_url("postgresql+psycopg://user:pass@host/db?sslmode=require"),
            "postgresql+psycopg://user:pass@host/db?sslmode=require",
        )


if __name__ == "__main__":
    unittest.main()
