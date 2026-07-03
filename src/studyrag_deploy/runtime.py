from __future__ import annotations

import argparse
import os

import uvicorn
from alembic import command
from alembic.config import Config

from .seed_sample_course import seed_sample_course


def run_migrations() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def seed_sample_course_if_enabled() -> None:
    if os.getenv("STUDYRAG_SEED_SAMPLE_COURSE_ON_STARTUP", "false").lower() in {"1", "true", "yes"}:
        course_id = seed_sample_course()
        print(f"Seeded sample course: {course_id}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="StudyRAG deployment runtime.")
    parser.add_argument("--migrate-only", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()

    if os.getenv("STUDYRAG_SKIP_MIGRATIONS", "false").lower() not in {"1", "true", "yes"}:
        run_migrations()

    seed_sample_course_if_enabled()

    if args.migrate_only or args.seed_only:
        return

    uvicorn.run(
        "studyrag_api.app:create_app",
        factory=True,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
