"""Đọc cấu hình thí nghiệm RAG từ biến môi trường."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else default


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}.") from exc


@dataclass(frozen=True)
class Settings:
    llm_provider: str = _env("RAG_LLM_PROVIDER", "ollama").lower()
    ollama_base_url: str = _env("RAG_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_llm_model: str = _env("RAG_OLLAMA_LLM_MODEL", "qwen2.5:3b")
    openai_base_url: str = _env("RAG_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_api_key: str = _env("RAG_OPENAI_API_KEY", "")
    openai_llm_model: str = _env("RAG_OPENAI_LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = _env("RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
    embedding_device: str = _env("RAG_EMBEDDING_DEVICE", "cpu")
    chunk_size: int = _env_int("RAG_CHUNK_SIZE", 800)
    chunk_overlap: int = _env_int("RAG_CHUNK_OVERLAP", 100)
    top_k: int = _env_int("RAG_TOP_K", 5)
    prompt_template: str = _env("RAG_PROMPT_TEMPLATE", "grounded")
    seed: int = _env_int("RAG_SEED", 7)

    def validate(self) -> None:
        if self.llm_provider not in {"ollama", "openai_compatible"}:
            raise ValueError(
                "RAG_LLM_PROVIDER must be 'ollama' or 'openai_compatible', "
                f"got {self.llm_provider!r}"
            )
        if self.llm_provider == "openai_compatible" and not self.openai_api_key:
            raise ValueError(
                "RAG_OPENAI_API_KEY is required when RAG_LLM_PROVIDER='openai_compatible'."
            )
        if self.chunk_size <= 0:
            raise ValueError("RAG_CHUNK_SIZE must be greater than zero.")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be >= 0 and smaller than chunk size.")
        if self.top_k <= 0:
            raise ValueError("RAG_TOP_K must be greater than zero.")
        if self.prompt_template != "grounded":
            raise ValueError("RAG_PROMPT_TEMPLATE must be 'grounded'.")


settings = Settings()
