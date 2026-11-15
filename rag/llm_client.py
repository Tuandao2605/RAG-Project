"""Client tối giản cho các LLM provider của pipeline RAG."""

from __future__ import annotations

import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rag.config import Settings


class ProviderError(RuntimeError):
    """Lỗi phát sinh khi không thể kết nối model provider đã cấu hình."""


def _post_json(
    url: str, payload: dict[str, object], headers: dict[str, str] | None = None
) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = getattr(exc, "reason", str(exc))
        raise ProviderError(f"Provider request failed: {detail}") from exc
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProviderError("Provider returned invalid JSON.") from exc
    if not isinstance(result, dict):
        raise ProviderError("Provider returned a JSON value instead of an object.")
    return result


def chat(
    prompt: str,
    config: Settings,
    temperature: float = 0.0,
    seed: int | None = None,
) -> str:
    """Gửi một yêu cầu chat không streaming tới LLM provider đã chọn."""
    config.validate()
    if not math.isfinite(temperature) or temperature < 0:
        raise ValueError("temperature must be a finite non-negative number")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None")
    if config.llm_provider == "ollama":
        options: dict[str, object] = {"temperature": temperature}
        if seed is not None:
            options["seed"] = seed
        response = _post_json(
            f"{config.ollama_base_url}/api/chat",
            {
                "model": config.ollama_llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"seed": config.seed, "temperature": 0},
            },
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderError("Ollama response did not contain message.content.")
        return message["content"]

    payload: dict[str, object] = {
        "model": config.openai_llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if seed is not None:
        payload["seed"] = seed
    response = _post_json(
        f"{config.openai_base_url}/chat/completions",
        {
            "model": config.openai_llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "seed": config.seed,
        },
        {"Authorization": "Bearer " + config.openai_api_key},
    )
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("OpenAI-compatible response did not contain choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ProviderError("OpenAI-compatible response contained an invalid choice.")
    message = first_choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ProviderError("OpenAI-compatible response did not contain message.content.")
    return message["content"]
