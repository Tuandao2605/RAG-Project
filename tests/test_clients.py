from unittest.mock import patch

from rag.clients import chat
from rag.config import Settings


def test_ollama_chat_returns_message_content() -> None:
    config = Settings(llm_provider="ollama")
    with patch(
        "rag.clients._post_json",
        return_value={"message": {"content": "safe response"}},
    ) as post:
        result = chat("hello", config)

    assert result == "safe response"
    post.assert_called_once()
    assert post.call_args.args[0] == "http://localhost:11434/api/chat"


def test_openai_compatible_chat_sends_authorization() -> None:
    config = Settings(
        llm_provider="openai_compatible",
        openai_api_key="test-key",
        openai_base_url="http://localhost:8000/v1",
    )
    with patch(
        "rag.clients._post_json",
        return_value={"choices": [{"message": {"content": "safe response"}}]},
    ) as post:
        result = chat("hello", config)

    assert result == "safe response"
    assert post.call_args.args[0] == "http://localhost:8000/v1/chat/completions"
    assert post.call_args.args[2] == {"Authorization": "Bearer test-key"}
