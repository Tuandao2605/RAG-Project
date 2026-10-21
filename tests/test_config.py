import pytest

from rag.config import Settings


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="RAG_OPENAI_API_KEY"):
        Settings(llm_provider="openai_compatible").validate()


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="RAG_LLM_PROVIDER"):
        Settings(llm_provider="unknown").validate()
