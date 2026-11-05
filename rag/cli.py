"""CLI build FAISS index và truy vấn top-k."""

from __future__ import annotations

import argparse
import json
import sys

from defenses.sandwich import DEFENSE_IDS, build_prompt
from rag.clients import chat
from rag.config import settings
from rag.index import build_index, load_index, save_index, search
from rag.ingest import load_chunks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query the RAG FAISS index.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-index", help="Ingest documents and build an index.")
    build.add_argument("--input", required=True, help="Markdown/JSONL file or directory.")
    build.add_argument("--output", required=True, help="Directory for index artifacts.")
    build.add_argument("--chunk-size", type=int, default=800)
    build.add_argument("--overlap", type=int, default=100)

    query = commands.add_parser("query", help="Search an existing index.")
    query.add_argument("--index", required=True, help="Directory containing index artifacts.")
    query.add_argument("--query", required=True, help="Question to retrieve against.")
    query.add_argument("--top-k", type=int, default=5)

    answer = commands.add_parser("answer", help="Retrieve context and answer using B0 or B1.")
    answer.add_argument("--index", required=True, help="Directory containing index artifacts.")
    answer.add_argument("--question", required=True, help="Question to answer.")
    answer.add_argument("--top-k", type=int, default=5)
    answer.add_argument("--defense", choices=DEFENSE_IDS, default="b0")
    answer.add_argument("--temperature", type=float, default=0.0)
    answer.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build-index":
            chunks = load_chunks(args.input, args.chunk_size, args.overlap)
            data = build_index(chunks, settings)
            save_index(data, args.output)
            print(f"Loaded chunks: {len(chunks)}")
            print(f"Saved index: {args.output}\\index.faiss")
            print(f"Saved metadata: {args.output}\\metadata.json")
            return 0
        data = load_index(args.index)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if args.command == "query":
            result = search(data, args.query, args.top_k, settings)
        else:
            retrieved = search(data, args.question, args.top_k, settings)
            prompt = build_prompt(args.question, retrieved, defense_id=args.defense)
            answer_text = chat(
                prompt,
                settings,
                temperature=args.temperature,
                seed=args.seed,
            )
            result = {
                "defense_id": args.defense,
                "answer": answer_text,
                "sources": retrieved,
                "temperature": args.temperature,
                "seed": args.seed,
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
