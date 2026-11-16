import json
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from rag.config import Settings
from rag.defenses import BaselineDefense
from rag.llm_client import ProviderError
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
            BaselineDefense(),
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
            BaselineDefense(),
            log_path,
        )

    assert result.answer is None
    assert result.trace["error"] == {
        "type": "RuntimeError",
        "message": "provider unavailable",
    }
    saved_trace = json.loads(log_path.read_text(encoding="utf-8"))
    assert saved_trace["latency_ms"]["total"] >= 0


def test_answer_pipeline_writes_runner_artifact_and_retry_latency(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    case = json.loads(
        (root / "attacks" / "cases" / "indirect_answer_override.json").read_text(
            encoding="utf-8"
        )
    )
    contexts = [
        {
            "chunk_id": "doc-refund-policy:0000",
            "doc_id": "doc-refund-policy",
            "text": "Khách hàng có thể hoàn trả trong 30 ngày.",
            "score": 0.9,
        }
    ]
    artifact_path = tmp_path / "runs.jsonl"
    latency_path = tmp_path / "latencies.jsonl"

    with (
        patch("rag.pipeline.search", return_value=contexts),
        patch(
            "rag.llm_client._chat_once",
            side_effect=[ProviderError("temporary"), "30 ngày"],
        ) as chat,
    ):
        result = answer_question(
            "Thời hạn hoàn trả là bao lâu?",
            IndexData(None, []),
            Settings(seed=7),
            BaselineDefense(),
            artifact_path=artifact_path,
            latency_path=latency_path,
            case=case,
            variant="clean",
        )

    assert result.answer == "30 ngày"
    assert result.trace["retry_count"] == 1
    assert chat.call_count == 2
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "completed"
    assert artifact["variant"] == "clean"
    assert artifact["context_chunks"][0]["chunk_id"] == "doc-refund-policy-0000"
    assert artifact["context_chunks"][0]["metadata"]["doc_id"] == "doc-refund-policy"
    latency = json.loads(latency_path.read_text(encoding="utf-8"))
    assert latency["run_id"] == artifact["run_id"]
    assert latency["retry_count"] == 1
    schema = json.loads((root / "schemas" / "security_case.schema.json").read_text())
    Draft202012Validator(
        {"$ref": "#/$defs/run_result", "$defs": schema["$defs"]}
    ).validate(artifact)
