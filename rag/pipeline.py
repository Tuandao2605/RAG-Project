"""Pipeline RAG chung cho B0 và các phiên bản có defense."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defenses.sandwich import build_prompt
from eval.artifacts import append_jsonl, append_latency, build_run_result
from rag.config import Settings
from rag.defenses import Context, ContextDefense, public_context
from rag.llm_client import ProviderError, chat
from rag.vector_index import IndexData, search


@dataclass(frozen=True)
class AnswerResult:
    trace: dict[str, Any]
    answer: str | None


def _config_snapshot(config: Settings, temperature: float, defense: ContextDefense) -> dict[str, object]:
    model = config.ollama_llm_model if config.llm_provider == "ollama" else config.openai_llm_model
    return {
        "chunk_size": config.chunk_size,
        "overlap": config.chunk_overlap,
        "top_k": config.top_k,
        "embedding_model": config.embedding_model,
        "llm_provider": config.llm_provider,
        "model": model,
        "prompt_template": config.prompt_template,
        "seed": config.seed,
        "provider": config.llm_provider,
        "defense_id": defense.name,
        "temperature": temperature,
    }


def _append_trace(path: str | Path | None, trace: dict[str, Any]) -> None:
    if path is None:
        return
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(trace, ensure_ascii=False) + "\n")


def answer_question(
    question: str,
    data: IndexData,
    config: Settings,
    defense: ContextDefense,
    log_path: str | Path | None = None,
    *,
    temperature: float = 0.0,
    artifact_path: str | Path | None = None,
    latency_path: str | Path | None = None,
    case: dict[str, Any] | None = None,
    variant: str | None = None,
) -> AnswerResult:
    """Chạy retrieval, defense, generation và trace trong một pipeline."""
    if not question.strip():
        raise ValueError("Question must not be empty.")
    config.validate()
    started = time.perf_counter()
    trace: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "question": question,
        "defense": defense.name,
        "context_before_defense": [],
        "context_after_defense": [],
        "answer": None,
        "citations": [],
        "config": _config_snapshot(config, temperature, defense),
        "latency_ms": {},
        "retry_count": 0,
        "error": None,
    }
    attempts: list[int] = []
    try:
        retrieval_started = time.perf_counter()
        contexts = search(data, question, config.top_k, config)
        trace["latency_ms"]["retrieval"] = round(
            (time.perf_counter() - retrieval_started) * 1000, 3
        )
        trace["context_before_defense"] = [public_context(context) for context in contexts]

        defense_started = time.perf_counter()
        safe_contexts: list[Context] = [
            public_context(context) for context in defense.apply(question, contexts)
        ]
        trace["latency_ms"]["defense"] = round((time.perf_counter() - defense_started) * 1000, 3)
        trace["context_after_defense"] = safe_contexts
        trace["citations"] = [
            {key: context[key] for key in ("chunk_id", "doc_id", "score") if key in context}
            for context in safe_contexts
        ]

        prompt = build_prompt(question, safe_contexts, defense.name)
        llm_started = time.perf_counter()
        answer = chat(prompt, config, temperature=temperature, seed=config.seed, attempts=attempts)
        trace["latency_ms"]["llm"] = round((time.perf_counter() - llm_started) * 1000, 3)
        trace["retry_count"] = max(attempts[-1] - 1, 0) if attempts else 0
        trace["answer"] = answer
        return AnswerResult(trace, answer)
    except (OSError, ProviderError, RuntimeError, ValueError) as exc:
        trace["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return AnswerResult(trace, None)
    finally:
        trace["latency_ms"]["total"] = round((time.perf_counter() - started) * 1000, 3)
        _append_trace(log_path, trace)
        if case is not None and variant is not None and artifact_path is not None:
            artifact = build_run_result(trace, case, variant, temperature=temperature)
            append_jsonl(artifact_path, artifact)
            if latency_path is not None:
                append_latency(
                    latency_path,
                    trace["run_id"],
                    trace["latency_ms"]["total"],
                    retry_count=trace["retry_count"],
                )
