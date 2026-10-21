"""Đọc cấu hình thí nghiệm RAG từ biến môi trường."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value else default


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


settings = Settings()
