from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def rate_limit_key(request: Request) -> str:
    if os.getenv("STUDYRAG_TRUST_PROXY_HEADERS", "true").lower() in {"1", "true", "yes"}:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", maxsplit=1)[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
