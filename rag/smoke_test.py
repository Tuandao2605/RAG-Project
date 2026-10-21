"""Kiểm tra LLM và embedding theo stack đã chọn.

Chạy bằng:
    python -m rag.smoke_test
"""

from __future__ import annotations

import sys

from rag.clients import ProviderError, chat, embed
from rag.config import settings


def main() -> int:
    try:
        settings.validate()
        response = chat(
            "Reply with exactly one short sentence: the RAG security smoke test works.",
            settings,
        )
        vectors = embed(
            [
                "Tài liệu này mô tả chính sách bảo mật.",
                "This document describes a security policy.",
            ],
            settings,
        )
    except (ProviderError, ValueError, OSError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1

    dimension = len(vectors[0]) if vectors else 0
    print(f"LLM provider: {settings.llm_provider}")
    print(f"LLM response: {response.strip()}")
    print(f"Embedding model: {settings.embedding_model}")
    print(f"Embedding shape: ({len(vectors)}, {dimension})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
