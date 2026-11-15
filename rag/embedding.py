"""Tạo embedding cho passage và câu hỏi bằng mô hình SentenceTransformers."""

from __future__ import annotations

from rag.config import Settings
from rag.llm_client import ProviderError


def _embed(texts: list[str], prefix: str, config: Settings) -> list[list[float]]:
    """Tạo embedding E5 cho danh sách văn bản với tiền tố phù hợp."""
    if not texts:
        raise ValueError("At least one text is required for embedding.")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ProviderError(
            "sentence-transformers is not installed. Run: "
            "python -m pip install -r requirements.txt"
        ) from exc

    model = SentenceTransformer(config.embedding_model, device=config.embedding_device)
    prefixed_texts = [f"{prefix}: {text}" for text in texts]
    vectors = model.encode(prefixed_texts, normalize_embeddings=True)
    return vectors.tolist()


def embed(texts: list[str], config: Settings) -> list[list[float]]:
    """Tạo embedding passage cho danh sách văn bản tài liệu."""
    return _embed(texts, "passage", config)


def embed_queries(texts: list[str], config: Settings) -> list[list[float]]:
    """Tạo embedding query cho danh sách câu hỏi."""
    return _embed(texts, "query", config)
