from __future__ import annotations

from typing import Protocol

from .models import GenerationRequest


class ResponseGenerator(Protocol):
    def generate(self, request: GenerationRequest) -> str:
        ...


class OpenAIChatResponseGenerator:
    """OpenAI-compatible chat generator for deployed answer synthesis."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only without optional LLM deps.
            raise RuntimeError("OpenAI-compatible generation requires the `openai` package") from exc

        if not api_key:
            raise ValueError("api_key is required")
        if not model:
            raise ValueError("model is required")

        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def generate(self, request: GenerationRequest) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
        )
        message = response.choices[0].message.content
        return message.strip() if message else ""
