from unittest.mock import patch

from rag.config import Settings
from rag.index import build_index, load_index, save_index, search
from rag.ingest import Chunk


def test_build_save_load_and_search_returns_metadata(tmp_path) -> None:
    chunks = [
        Chunk("doc-a:0000", "doc-a", "password policy"),
        Chunk("doc-b:0000", "doc-b", "incident response"),
    ]
    config = Settings()
    with (
        patch("rag.index.embed", return_value=[[1.0, 0.0], [0.0, 1.0]]),
        patch("rag.index.embed_queries", return_value=[[1.0, 0.0]]),
    ):
        data = build_index(chunks, config)
        save_index(data, tmp_path)
        loaded = load_index(tmp_path)
        results = search(loaded, "password policy", 1, config)

    assert results[0]["chunk_id"] == "doc-a:0000"
    assert results[0]["doc_id"] == "doc-a"
    assert results[0]["score"] == 1.0


def test_empty_index_returns_empty_results(tmp_path) -> None:
    config = Settings()
    data = build_index([], config)
    save_index(data, tmp_path)
    loaded = load_index(tmp_path)

    with patch("rag.index.embed_queries") as embed_query:
        assert search(loaded, "anything", 3, config) == []
        embed_query.assert_not_called()
