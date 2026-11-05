"""Xây dựng, lưu, nạp và truy vấn chỉ mục FAISS."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from rag.clients import embed, embed_queries
from rag.config import Settings
from rag.ingest import Chunk


@dataclass(frozen=True)
class IndexData:
    index: Any
    metadata: list[dict[str, str]]


def build_index(chunks: list[Chunk], config: Settings) -> IndexData:
    """Tạo FAISS inner-product index từ các chunk đã ingest."""
    if not chunks:
        return IndexData(faiss.IndexFlatIP(1), [])
    vectors = np.asarray(embed([chunk.text for chunk in chunks], config), dtype="float32")
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise ValueError("Embedding output does not match the number of chunks.")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    metadata = [
        {"chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id, "text": chunk.text} for chunk in chunks
    ]
    return IndexData(index, metadata)


def save_index(data: IndexData, output_dir: str | Path) -> None:
    """Lưu FAISS index và metadata JSON vào một thư mục."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    faiss.write_index(data.index, str(directory / "index.faiss"))
    (directory / "metadata.json").write_text(
        json.dumps(data.metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_index(index_dir: str | Path) -> IndexData:
    """Nạp FAISS index và metadata, đồng thời kiểm tra tính nhất quán."""
    directory = Path(index_dir)
    index_path = directory / "index.faiss"
    metadata_path = directory / "metadata.json"
    if not index_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(f"Index requires {index_path.name} and {metadata_path.name}.")
    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, list) or not all(isinstance(item, dict) for item in metadata):
        raise ValueError("metadata.json must contain a list of objects.")
    if index.ntotal != len(metadata):
        raise ValueError("FAISS index and metadata have different numbers of entries.")
    return IndexData(index, metadata)


def search(
    data: IndexData, query: str, top_k: int, config: Settings
) -> list[dict[str, str | float]]:
    """Tìm top-k chunk gần nhất và trả về metadata cùng cosine score."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")
    if not query.strip() or not data.metadata or data.index.ntotal == 0:
        return []
    vector = np.asarray(embed_queries([query], config), dtype="float32")
    scores, positions = data.index.search(vector, min(top_k, data.index.ntotal))
    results: list[dict[str, str | float]] = []
    for score, position in zip(scores[0], positions[0], strict=True):
        if position < 0:
            continue
        result = dict(data.metadata[int(position)])
        result["score"] = float(score)
        results.append(result)
    return results
