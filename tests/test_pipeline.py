import json
from unittest.mock import patch

from rag.config import Settings
from rag.defenses import NoOpDefense
from rag.pipeline import answer_question
from rag.vector_index import IndexData


def test_answer_pipeline_logs_context_prompt_answer_and_latency(tmp_path) -> None:
    config = Settings(top_k=2, seed=11)
    contexts = [
        {
            "chunk_id": "policy:0000",
            "doc_id": "policy",
            "text": "Mật khẩu phải có ít nhất 12 ký tự.",
            "score": 0.9,
        }
    ]
    log_path = tmp_path / "runs.jsonl"

    with (
        patch("rag.pipeline.search", return_value=contexts),
        patch("rag.pipeline.chat", return_value="Mật khẩu phải có ít nhất 12 ký tự.") as chat,
    ):
        result = answer_question(
            "Mật khẩu cần dài bao nhiêu?",
            IndexData(None, []),
            config,
            NoOpDefense(),
            log_path,
        )

    assert result.answer == "Mật khẩu phải có ít nhất 12 ký tự."
    assert result.trace["context_before_defense"] == contexts
    assert result.trace["context_after_defense"] == contexts
    assert result.trace["citations"][0]["chunk_id"] == "policy:0000"
    assert result.trace["latency_ms"]["total"] >= 0
    assert result.trace["error"] is None
    chat.assert_called_once()
    assert "policy:0000" in chat.call_args.args[0]
    saved_trace = json.loads(log_path.read_text(encoding="utf-8"))
    assert saved_trace["answer"] == result.answer
    assert saved_trace["config"]["seed"] == 11


def test_answer_pipeline_logs_provider_error(tmp_path) -> None:
    log_path = tmp_path / "runs.jsonl"
    with (
        patch("rag.pipeline.search", return_value=[]),
        patch("rag.pipeline.chat", side_effect=RuntimeError("provider unavailable")),
    ):
        result = answer_question(
            "Câu hỏi",
            IndexData(None, []),
            Settings(),
            NoOpDefense(),
            log_path,
        )

    assert result.answer is None
    assert result.trace["error"] == {
        "type": "RuntimeError",
        "message": "provider unavailable",
    }
    saved_trace = json.loads(log_path.read_text(encoding="utf-8"))
    assert saved_trace["latency_ms"]["total"] >= 0
