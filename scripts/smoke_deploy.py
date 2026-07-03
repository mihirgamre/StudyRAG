from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class ApiResponse:
    status: int
    body: Any
    content_type: str


def request_json(base_url: str, method: str, path: str, *, token: str | None = None, body: dict | None = None) -> ApiResponse:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(urljoin(base_url, path), data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            content = response.read().decode("utf-8")
            return ApiResponse(
                status=response.status,
                body=json.loads(content) if content else None,
                content_type=response.headers.get("content-type", ""),
            )
    except HTTPError as exc:
        content = exc.read().decode("utf-8")
        try:
            body_data = json.loads(content)
        except json.JSONDecodeError:
            body_data = content
        return ApiResponse(status=exc.code, body=body_data, content_type=exc.headers.get("content-type", ""))


def request_sse(base_url: str, path: str, *, token: str, body: dict) -> tuple[int, list[dict[str, Any]], str]:
    request = Request(
        urljoin(base_url, path),
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            content = response.read().decode("utf-8")
            return response.status, parse_sse(content), response.headers.get("content-type", "")
    except HTTPError as exc:
        return exc.code, [], exc.headers.get("content-type", "")


def parse_sse(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test a deployed StudyRAG API.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", default=f"studyrag.smoke.{uuid.uuid4().hex}@gmail.com")
    parser.add_argument("--password", default="correct horse battery staple")
    parser.add_argument("--sample-course-name", default="StudyRAG Sample Course")
    parser.add_argument("--question", default="What base case does the factorial recursion method use?")
    parser.add_argument("--check-rate-limit", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    register = request_json(base_url, "POST", "/auth/register", body={"email": args.email, "password": args.password})
    if register.status != 201:
        raise SystemExit(f"register failed: {register.status} {register.body}")

    login = request_json(base_url, "POST", "/auth/login", body={"email": args.email, "password": args.password})
    if login.status != 200:
        raise SystemExit(f"login failed: {login.status} {login.body}")

    token = login.body["access_token"]
    courses = request_json(base_url, "GET", "/courses", token=token)
    sample_courses = [course for course in courses.body if course["name"] == args.sample_course_name]
    if not sample_courses:
        raise SystemExit(f"sample course not found in {courses.body}")

    course_id = sample_courses[0]["id"]
    conversation = request_json(base_url, "POST", f"/courses/{course_id}/conversations", token=token)
    if conversation.status != 201:
        raise SystemExit(f"conversation creation failed: {conversation.status} {conversation.body}")

    status, events, content_type = request_sse(
        base_url,
        f"/conversations/{conversation.body['id']}/messages",
        token=token,
        body={"content": args.question},
    )
    if status != 200 or "text/event-stream" not in content_type:
        raise SystemExit(f"message stream failed: {status} {content_type}")

    final_events = [event["data"] for event in events if event["event"] == "final"]
    if not final_events:
        raise SystemExit("stream did not include final event")
    final = final_events[0]
    if final["refused"] or not (1 <= len(final["citations"]) <= 4):
        raise SystemExit(f"unexpected final response: {final}")

    rate_limit_status = None
    if args.check_rate_limit:
        for index in range(35):
            status, _, _ = request_sse(
                base_url,
                f"/conversations/{conversation.body['id']}/messages",
                token=token,
                body={"content": f"Rate limit probe {index}: {args.question}"},
            )
            if status == 429:
                rate_limit_status = 429
                break
            time.sleep(0.05)
        if rate_limit_status != 429:
            raise SystemExit("rate limit probe did not receive 429")

    print(
        json.dumps(
            {
                "registered": args.email,
                "course_id": course_id,
                "conversation_id": conversation.body["id"],
                "stream_final_received": True,
                "citation_count": len(final["citations"]),
                "confidence": final["confidence"],
                "rate_limit_status": rate_limit_status,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
