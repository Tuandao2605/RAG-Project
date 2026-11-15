"""CLI build FAISS index và truy vấn top-k."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace

from rag.config import Settings, settings
from rag.defenses import create_defense
from rag.ingest import load_chunks
from rag.pipeline import answer_question
from rag.vector_index import build_index, load_index, save_index, search


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query the RAG FAISS index.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-index", help="Ingest documents and build an index.")
    build.add_argument("--input", required=True, help="Markdown/JSONL file or directory.")
    build.add_argument("--output", required=True, help="Directory for index artifacts.")
    build.add_argument("--chunk-size", type=int, default=None)
    build.add_argument("--overlap", type=int, default=None)

    query = commands.add_parser("query", help="Search an existing index.")
    query.add_argument("--index", required=True, help="Directory containing index artifacts.")
    query.add_argument("--query", required=True, help="Question to retrieve against.")
    query.add_argument("--top-k", type=int, default=None)

    answer = commands.add_parser("answer", help="Retrieve context and generate a cited answer.")
    answer.add_argument("--index", required=True, help="Directory containing index artifacts.")
    answer.add_argument("--query", required=True, help="Question to answer.")
    answer.add_argument("--top-k", type=int, default=None)
    answer.add_argument("--defense", default="noop", help="Defense hook name.")
    answer.add_argument("--seed", type=int, default=None)
    answer.add_argument("--log", default=None, help="JSONL trace output path.")
    return parser


def _settings_for_args(args: argparse.Namespace) -> Settings:
    updates: dict[str, object] = {}
    if args.command in {"query", "answer"} and args.top_k is not None:
        updates["top_k"] = args.top_k
    if args.command == "build-index":
        if args.chunk_size is not None:
            updates["chunk_size"] = args.chunk_size
        if args.overlap is not None:
            updates["chunk_overlap"] = args.overlap
    if args.command == "answer" and args.seed is not None:
        updates["seed"] = args.seed
    return replace(settings, **updates)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = _settings_for_args(args)
        if args.command == "build-index":
            chunks = load_chunks(args.input, config.chunk_size, config.chunk_overlap)
            data = build_index(chunks, config)
            save_index(data, args.output)
            print(f"Loaded chunks: {len(chunks)}")
            print(f"Saved index: {args.output}\\index.faiss")
            print(f"Saved metadata: {args.output}\\metadata.json")
            return 0
        data = load_index(args.index)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if args.command == "answer":
            result = answer_question(
                args.query,
                data,
                config,
                create_defense(args.defense),
                args.log,
            )
            print(json.dumps(result.trace, ensure_ascii=False, indent=2))
            return 0 if result.answer is not None else 1
        print(
            json.dumps(search(data, args.query, config.top_k, config), ensure_ascii=False, indent=2)
        )
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
