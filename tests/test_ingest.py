import json

import pytest

from rag.ingest import chunk_text, load_chunks, read_documents


def test_read_documents_supports_markdown_and_jsonl(tmp_path) -> None:
    (tmp_path / "policy.md").write_text("# Policy\nUse MFA.", encoding="utf-8")
    (tmp_path / "records.jsonl").write_text(
        json.dumps({"doc_id": "json-1", "text": "Keep secrets out of logs."}) + "\n",
        encoding="utf-8",
    )

    documents = read_documents(tmp_path)
    chunks = load_chunks(tmp_path, chunk_size=100, overlap=0)

    assert {doc_id for doc_id, _ in documents} == {"policy", "json-1"}
    assert chunks[0].chunk_id.endswith(":0000")
    assert {chunk.doc_id for chunk in chunks} == {"policy", "json-1"}


def test_chunk_text_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("text", chunk_size=10, overlap=10)
