"""Adapt pipeline traces to the benchmark run-result and latency artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _document_metadata(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        document["metadata"]["doc_id"]: document["metadata"]
        for document in case["documents"]
    }


def _safe_chunk_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()
    if not safe:
        raise ValueError("chunk_id must contain at least one valid identifier character")
    return safe


def build_run_result(
    trace: dict[str, Any],
    case: dict[str, Any],
    variant: str,
    *,
    temperature: float = 0.0,
    seed: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    trace_complete: bool | None = None,
    egress_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convert a pipeline trace into the schema consumed by ``eval.runner``."""
    if variant not in {"clean", "attack"}:
        raise ValueError("variant must be 'clean' or 'attack'")
    if not isinstance(trace.get("run_id"), str):
        raise ValueError("trace must contain a string run_id")

    metadata_by_doc = _document_metadata(case)
    contexts = trace.get("context_after_defense", [])
    context_chunks = []
    for context in contexts:
        doc_id = context.get("doc_id")
        if not isinstance(doc_id, str) or doc_id not in metadata_by_doc:
            raise ValueError(f"Trace context references unknown doc_id {doc_id!r}")
        text = context.get("text")
        chunk_id = context.get("chunk_id")
        if not isinstance(text, str) or not isinstance(chunk_id, str):
            raise ValueError("Trace contexts require string chunk_id and text")
        context_chunks.append(
            {
                "chunk_id": _safe_chunk_id(chunk_id),
                "metadata": metadata_by_doc[doc_id],
                "content": text,
            }
        )

    config = trace.get("config")
    if not isinstance(config, dict):
        raise ValueError("Trace must contain config")
    resolved_provider = provider or config.get("llm_provider")
    resolved_model = model or config.get("model")
    if not isinstance(resolved_provider, str) or not isinstance(resolved_model, str):
        raise ValueError("provider and model are required for benchmark artifacts")

    error = trace.get("error")
    status = "completed" if error is None and isinstance(trace.get("answer"), str) else "error"
    answer = trace.get("answer") if isinstance(trace.get("answer"), str) else ""
    complete = status == "completed" if trace_complete is None else trace_complete
    return {
        "schema_version": "1.0.0",
        "case_id": case["case_id"],
        "run_id": trace["run_id"],
        "variant": variant,
        "status": status,
        "config": {
            "provider": resolved_provider,
            "model": resolved_model,
            "defense_id": trace.get("defense", "unknown"),
            "temperature": temperature,
            "seed": seed if seed is not None else config.get("seed"),
        },
        "trace_complete": bool(complete),
        "candidate_doc_ids": case["retrieval"]["candidate_doc_ids"],
        "context_chunks": context_chunks,
        "answer": answer,
        "citations": [
            {"doc_id": citation["doc_id"], "chunk_id": _safe_chunk_id(citation["chunk_id"])}
            for citation in trace.get("citations", [])
            if isinstance(citation, dict)
            and isinstance(citation.get("doc_id"), str)
            and isinstance(citation.get("chunk_id"), str)
        ],
        "egress_events": egress_events or [],
        "error": None if status == "completed" else str(error or "pipeline failed"),
    }


def append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    """Append one JSON object, creating its parent directory when needed."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_latency(
    path: str | Path,
    run_id: str,
    latency_ms: float,
    *,
    cache_hit: bool = False,
    retry_count: int = 0,
) -> None:
    if latency_ms < 0 or retry_count < 0:
        raise ValueError("latency_ms and retry_count must be non-negative")
    append_jsonl(
        path,
        {
            "run_id": run_id,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
            "retry_count": retry_count,
        },
    )
