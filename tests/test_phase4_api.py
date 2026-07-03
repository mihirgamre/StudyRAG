import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

TEST_DATABASE_URL = os.getenv("STUDYRAG_TEST_DATABASE_URL")

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, func, select, text
    from sqlalchemy.orm import sessionmaker

    from studyrag_api import create_app
    from studyrag_core import ConfidenceGate, HashingEmbeddingModel
    from eval.course_material import COURSE_NAME
    from studyrag_ingestion import LocalObjectStorage
    from studyrag_persistence import Base
    from studyrag_persistence.models import MessageCitationRecord
    from studyrag_deploy.seed_sample_course import seed_sample_course

    from test_ingestion_pipeline import _small_pdf_bytes

    IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - exercised only without optional phase deps.
    IMPORT_ERROR = exc


@unittest.skipUnless(TEST_DATABASE_URL, "set STUDYRAG_TEST_DATABASE_URL to run Phase 4 API tests")
@unittest.skipIf(IMPORT_ERROR is not None, f"Phase 4 dependencies are not installed: {IMPORT_ERROR}")
class Phase4ApiTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.storage_dir.cleanup()

    def test_register_login_upload_ask_streams_answer_and_persists_citations(self) -> None:
        client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.05))
        token = self._register(client, "student@example.com")
        login_token = self._login(client, "student@example.com")
        self.assertNotEqual(login_token, "")

        course_id = self._create_course(client, token, "Calculus II")
        self._upload_pdf(
            client,
            token,
            course_id,
            "Related Rates. Related rates problems connect changing quantities over time. "
            "Differentiate with respect to time and solve for the unknown rate.",
        )
        conversation_id = self._create_conversation(client, token, course_id)

        response = client.post(
            f"/conversations/{conversation_id}/messages",
            headers=_auth_headers(token),
            json={"content": "How do I solve related rates problems over time?"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/event-stream")
        events = _parse_sse(response.text)
        token_text = "".join(event["data"]["text"] for event in events if event["event"] == "token")
        final = [event["data"] for event in events if event["event"] == "final"][0]

        self.assertIn("Related rates problems", token_text)
        self.assertFalse(final["refused"])
        self.assertGreater(final["confidence"], 0.0)
        self.assertGreaterEqual(len(final["citations"]), 1)
        self.assertIn("[source 1]", final["answer"])

        with self.Session() as session:
            citation_count = session.scalar(select(func.count()).select_from(MessageCitationRecord))
            self.assertGreater(citation_count, 0)

    def test_user_a_cannot_read_user_b_course_or_conversation(self) -> None:
        client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.05))
        token_a = self._register(client, "a@example.com")
        token_b = self._register(client, "b@example.com")
        course_b = self._create_course(client, token_b, "Private Course")
        conversation_b = self._create_conversation(client, token_b, course_b)

        course_response = client.get(f"/courses/{course_b}", headers=_auth_headers(token_a))
        messages_response = client.get(f"/conversations/{conversation_b}/messages", headers=_auth_headers(token_a))
        ask_response = client.post(
            f"/conversations/{conversation_b}/messages",
            headers=_auth_headers(token_a),
            json={"content": "Can I read this?"},
        )

        self.assertEqual(course_response.status_code, 404)
        self.assertEqual(messages_response.status_code, 404)
        self.assertEqual(ask_response.status_code, 404)

    def test_user_a_cannot_list_user_b_documents(self) -> None:
        client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.05))
        token_a = self._register(client, "a@example.com")
        token_b = self._register(client, "b@example.com")
        course_b = self._create_course(client, token_b, "Private Course")
        self._upload_pdf(
            client,
            token_b,
            course_b,
            "Private derivative notes. The derivative measures instantaneous rate of change.",
        )

        owner_response = client.get(f"/courses/{course_b}/documents", headers=_auth_headers(token_b))
        cross_user_response = client.get(f"/courses/{course_b}/documents", headers=_auth_headers(token_a))

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(len(owner_response.json()), 1)
        self.assertTrue(owner_response.json()[0]["storage_url"].startswith("local://documents/"))
        self.assertEqual(cross_user_response.status_code, 404)

    def test_refusal_path_returns_not_enough_information_through_http_stack(self) -> None:
        client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.99))
        token = self._register(client, "student@example.com")
        course_id = self._create_course(client, token, "Calculus II")
        self._upload_pdf(
            client,
            token,
            course_id,
            "Related Rates. Related rates connect changing quantities over time.",
        )
        conversation_id = self._create_conversation(client, token, course_id)

        response = client.post(
            f"/conversations/{conversation_id}/messages",
            headers=_auth_headers(token),
            json={"content": "What does the syllabus say about late homework grading?"},
        )

        self.assertEqual(response.status_code, 200)
        final = [event["data"] for event in _parse_sse(response.text) if event["event"] == "final"][0]
        self.assertTrue(final["refused"])
        self.assertEqual(final["citations"], [])
        self.assertIn("don't have enough information", final["answer"])

    def test_demo_auth_seeded_sample_course_streams_cited_answer(self) -> None:
        seed_sample_course(self.engine, demo_email="demo@studyrag.local")

        with patch.dict(
            os.environ,
            {
                "STUDYRAG_DEMO_ENABLED": "true",
                "STUDYRAG_DEMO_USER_EMAIL": "demo@studyrag.local",
            },
        ):
            client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.05))
            demo_response = client.post("/auth/demo")

        self.assertEqual(demo_response.status_code, 200)
        token = demo_response.json()["access_token"]
        courses_response = client.get("/courses", headers=_auth_headers(token))
        self.assertEqual(courses_response.status_code, 200)
        sample_courses = [course for course in courses_response.json() if course["name"] == COURSE_NAME]
        self.assertEqual(len(sample_courses), 1)
        course_id = uuid.UUID(sample_courses[0]["id"])

        documents_response = client.get(f"/courses/{course_id}/documents", headers=_auth_headers(token))
        self.assertEqual(documents_response.status_code, 200)
        self.assertEqual(len(documents_response.json()), 1)
        self.assertEqual(documents_response.json()[0]["status"], "embedded")

        conversation_id = self._create_conversation(client, token, course_id)
        answer_response = client.post(
            f"/conversations/{conversation_id}/messages",
            headers=_auth_headers(token),
            json={"content": "How do related rates problems connect changing quantities over time?"},
        )

        self.assertEqual(answer_response.status_code, 200)
        final = [event["data"] for event in _parse_sse(answer_response.text) if event["event"] == "final"][0]
        self.assertFalse(final["refused"])
        self.assertGreaterEqual(len(final["citations"]), 1)
        self.assertLessEqual(len(final["citations"]), 4)
        self.assertIn("[source", final["answer"])

    def test_registered_user_gets_sample_course_and_streamed_cited_answer_when_enabled(self) -> None:
        with patch.dict(os.environ, {"STUDYRAG_ATTACH_SAMPLE_COURSE_ON_REGISTER": "true"}):
            client = self._client(confidence_gate=ConfidenceGate(min_similarity=0.05))
            token = self._register(client, "student@example.com")
            login_token = self._login(client, "student@example.com")

        courses_response = client.get("/courses", headers=_auth_headers(login_token))
        self.assertEqual(courses_response.status_code, 200)
        sample_courses = [course for course in courses_response.json() if course["name"] == COURSE_NAME]
        self.assertEqual(len(sample_courses), 1)
        course_id = uuid.UUID(sample_courses[0]["id"])

        documents_response = client.get(f"/courses/{course_id}/documents", headers=_auth_headers(token))
        self.assertEqual(documents_response.status_code, 200)
        self.assertEqual(documents_response.json()[0]["status"], "embedded")

        conversation_id = self._create_conversation(client, token, course_id)
        answer_response = client.post(
            f"/conversations/{conversation_id}/messages",
            headers=_auth_headers(token),
            json={"content": "What base case does the factorial recursion method use?"},
        )

        self.assertEqual(answer_response.status_code, 200)
        final = [event["data"] for event in _parse_sse(answer_response.text) if event["event"] == "final"][0]
        self.assertFalse(final["refused"])
        self.assertGreaterEqual(len(final["citations"]), 1)
        self.assertLessEqual(len(final["citations"]), 4)
        self.assertIn("[source", final["answer"])

    def _client(self, *, confidence_gate: ConfidenceGate) -> TestClient:
        app = create_app(
            engine=self.engine,
            storage=LocalObjectStorage(self.storage_dir.name),
            embedding_model=self.embedding_model,
            confidence_gate=confidence_gate,
            jwt_secret="test-secret-with-at-least-thirty-two-bytes",
        )
        return TestClient(app)

    def _register(self, client: TestClient, email: str) -> str:
        response = client.post(
            "/auth/register",
            json={"email": email, "password": "correct horse battery staple"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["access_token"]

    def _login(self, client: TestClient, email: str) -> str:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "correct horse battery staple"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def _create_course(self, client: TestClient, token: str, name: str) -> uuid.UUID:
        response = client.post("/courses", headers=_auth_headers(token), json={"name": name})
        self.assertEqual(response.status_code, 201)
        return uuid.UUID(response.json()["id"])

    def _create_conversation(self, client: TestClient, token: str, course_id: uuid.UUID) -> uuid.UUID:
        response = client.post(f"/courses/{course_id}/conversations", headers=_auth_headers(token))
        self.assertEqual(response.status_code, 201)
        return uuid.UUID(response.json()["id"])

    def _upload_pdf(self, client: TestClient, token: str, course_id: uuid.UUID, text: str) -> uuid.UUID:
        response = client.post(
            f"/courses/{course_id}/documents",
            headers=_auth_headers(token),
            files={"file": ("notes.pdf", _small_pdf_bytes(text), "application/pdf")},
        )
        self.assertEqual(response.status_code, 201)
        document_id = uuid.UUID(response.json()["id"])
        status_response = client.get(f"/documents/{document_id}/status", headers=_auth_headers(token))
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "embedded")
        return document_id


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split("\n\n"):
        event_name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        if event_name and data is not None:
            events.append({"event": event_name, "data": data})
    return events


if __name__ == "__main__":
    unittest.main()
