import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TEST_DATABASE_URL = os.getenv("STUDYRAG_TEST_DATABASE_URL")

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, func, select, text
    from sqlalchemy.orm import sessionmaker

    from studyrag_api import create_app
    from studyrag_core import ConfidenceGate, HashingEmbeddingModel
    from studyrag_ingestion import LocalObjectStorage
    from studyrag_persistence import Base, PostgresHybridRetriever
    from studyrag_persistence.models import ChunkRecord, CourseRecord, DocumentRecord, UserRecord

    IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - exercised only without optional phase deps.
    IMPORT_ERROR = exc


@unittest.skipUnless(TEST_DATABASE_URL, "set STUDYRAG_TEST_DATABASE_URL to run Postgres ingestion tests")
@unittest.skipIf(IMPORT_ERROR is not None, f"ingestion dependencies are not installed: {IMPORT_ERROR}")
class IngestionPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(TEST_DATABASE_URL, future=True)
        with cls.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.storage_dir = tempfile.TemporaryDirectory()
        self.embedding_model = HashingEmbeddingModel()
        self.app = create_app(
            engine=self.engine,
            storage=LocalObjectStorage(self.storage_dir.name),
            embedding_model=self.embedding_model,
            confidence_gate=ConfidenceGate(min_similarity=0.05),
            jwt_secret="test-secret-with-at-least-thirty-two-bytes",
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.storage_dir.cleanup()

    def test_small_pdf_upload_ingests_extracts_embeds_and_retrieves(self) -> None:
        token = self._register("student@example.com")
        course_id = self._create_course(token, "Calculus II")
        pdf_bytes = _small_pdf_bytes(
            "Related Rates. Related rates problems connect changing quantities over time. "
            "Differentiate with respect to time and solve for the unknown rate."
        )

        response = self.client.post(
            f"/courses/{course_id}/documents",
            headers=_auth_headers(token),
            files={"file": ("related-rates.pdf", pdf_bytes, "application/pdf")},
        )

        self.assertEqual(response.status_code, 201)
        document_id = uuid.UUID(response.json()["id"])
        status_response = self.client.get(f"/documents/{document_id}/status", headers=_auth_headers(token))

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "embedded")
        self.assertTrue(status_response.json()["storage_url"].startswith("local://documents/"))

        with self.Session() as session:
            document = session.get(DocumentRecord, document_id)
            self.assertIsNotNone(document)
            self.assertEqual(document.status, "embedded")
            self.assertEqual(document.source_type, "pdf")
            self.assertTrue(document.storage_url.startswith("local://documents/"))
            chunk_count = session.scalar(
                select(func.count()).select_from(ChunkRecord).where(ChunkRecord.document_id == document_id)
            )
            self.assertGreater(chunk_count, 0)

            retriever = PostgresHybridRetriever(session, self.embedding_model)
            hits = retriever.retrieve(str(course_id), "related rates time derivative", top_k=3)
            self.assertGreaterEqual(len(hits), 1)
            self.assertEqual(hits[0].chunk.document_id, str(document_id))
            self.assertEqual(hits[0].chunk.course_id, str(course_id))
            self.assertGreater(hits[0].vector_score, 0.0)
            self.assertGreater(hits[0].keyword_score, 0.0)

    def test_corrupt_pdf_upload_fails_document_status_without_crashing(self) -> None:
        token = self._register("student@example.com")
        course_id = self._create_course(token, "Calculus II")

        response = self.client.post(
            f"/courses/{course_id}/documents",
            headers=_auth_headers(token),
            files={"file": ("corrupt.pdf", b"not a real pdf", "application/pdf")},
        )

        self.assertEqual(response.status_code, 201)
        document_id = uuid.UUID(response.json()["id"])
        status_response = self.client.get(f"/documents/{document_id}/status", headers=_auth_headers(token))

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "failed")

        with self.Session() as session:
            document = session.get(DocumentRecord, document_id)
            self.assertIsNotNone(document)
            self.assertEqual(document.status, "failed")
            self.assertTrue(document.storage_url.startswith("local://documents/"))
            chunk_count = session.scalar(
                select(func.count()).select_from(ChunkRecord).where(ChunkRecord.document_id == document_id)
            )
            self.assertEqual(chunk_count, 0)

    def _register(self, email: str) -> str:
        response = self.client.post(
            "/auth/register",
            json={"email": email, "password": "correct horse battery staple"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["access_token"]

    def _create_course(self, token: str, name: str) -> uuid.UUID:
        response = self.client.post("/courses", headers=_auth_headers(token), json={"name": name})
        self.assertEqual(response.status_code, 201)
        return uuid.UUID(response.json()["id"])


def _small_pdf_bytes(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
