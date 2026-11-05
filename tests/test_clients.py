from unittest.mock import patch

from rag.clients import chat
from rag.config import Settings


def test_ollama_chat_returns_message_content() -> None:
    config = Settings(llm_provider="ollama")
    with patch(
        "rag.clients._post_json",
        return_value={"message": {"content": "safe response"}},
    ) as post:
        result = chat("hello", config, temperature=0.25, seed=7)

    assert result == "safe response"
    post.assert_called_once()
    assert post.call_args.args[0] == "http://localhost:11434/api/chat"
    assert post.call_args.args[1]["options"] == {"temperature": 0.25, "seed": 7}


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
        result = chat("hello", config, temperature=0.25, seed=7)

    assert result == "safe response"
    assert post.call_args.args[0] == "http://localhost:8000/v1/chat/completions"
    assert post.call_args.args[2] == {"Authorization": "Bearer test-key"}
    assert post.call_args.args[1]["temperature"] == 0.25
    assert post.call_args.args[1]["seed"] == 7


def test_chat_rejects_invalid_sampling_parameters() -> None:
    config = Settings(llm_provider="ollama")
    for temperature, seed in [(-0.1, None), (float("inf"), None), (0.0, True)]:
        try:
            chat("hello", config, temperature=temperature, seed=seed)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid sampling parameters should be rejected")
