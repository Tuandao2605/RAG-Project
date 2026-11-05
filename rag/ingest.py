"""Đọc tài liệu nguồn và chia thành các chunk để lập chỉ mục."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _read_markdown(path: Path) -> list[tuple[str, str]]:
    text = _clean_text(path.read_text(encoding="utf-8"))
    return [(path.stem, text)] if text else []


def _read_jsonl(path: Path) -> list[tuple[str, str]]:
    documents: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}.") from exc
            if not isinstance(record, dict):
                raise ValueError(f"JSONL record must be an object in {path}:{line_number}.")
            text = record.get("text", record.get("content"))
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"JSONL record needs non-empty text in {path}:{line_number}.")
            doc_id = record.get("doc_id", f"{path.stem}-{line_number}")
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError(
                    f"JSONL doc_id must be a non-empty string in {path}:{line_number}."
                )
            documents.append((doc_id.strip(), _clean_text(text)))
    return documents


def read_documents(input_path: str | Path) -> list[tuple[str, str]]:
    """Đọc một file hoặc toàn bộ file Markdown/JSONL trong thư mục."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")
    paths = (
        [path]
        if path.is_file()
        else sorted(item for item in path.rglob("*") if item.suffix.lower() in {".md", ".jsonl"})
    )
    documents: list[tuple[str, str]] = []
    for item in paths:
        if item.suffix.lower() == ".md":
            documents.extend(_read_markdown(item))
        elif item.suffix.lower() == ".jsonl":
            documents.extend(_read_jsonl(item))
    return documents


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Chia text theo ký tự, ưu tiên kết thúc ở khoảng trắng."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size.")
    cleaned = _clean_text(text)
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        if end < len(cleaned):
            boundary = cleaned.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = end - overlap
    return chunks


def load_chunks(input_path: str | Path, chunk_size: int = 800, overlap: int = 100) -> list[Chunk]:
    """Đọc tài liệu và tạo metadata định danh cho từng chunk."""
    chunks: list[Chunk] = []
    for doc_id, text in read_documents(input_path):
        for number, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
            chunks.append(Chunk(f"{doc_id}:{number:04d}", doc_id, chunk))
    return chunks
