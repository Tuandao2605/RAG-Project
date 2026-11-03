"""Kiểm thử bộ dữ liệu pilot Sprint 2 (ticket 2.2, 2.4, 2.10).

Các test ở đây chạy offline, không cần model hay API key. Chúng gọi lại CLI của
generator và validator để bảo đảm artifact đã commit khớp với seed và mọi kiểm
tra nhãn đều đạt.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_generator_matches_committed_artifact() -> None:
    result = run_script("attacks/generate_dev_cases.py", "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_validator_passes_all_checks() -> None:
    result = run_script("attacks/validate_dataset.py")
    assert result.returncode == 0, result.stdout + result.stderr


def test_corpus_and_qa_meet_sprint_2_minimums() -> None:
    docs = read_jsonl(ROOT / "data" / "corpus" / "docs.jsonl")
    qa = read_jsonl(ROOT / "data" / "qa" / "dev.jsonl") + read_jsonl(
        ROOT / "data" / "qa" / "test.jsonl"
    )
    assert len(docs) >= 20
    assert len(qa) >= 20
    assert len({doc["metadata"]["doc_id"] for doc in docs}) == len(docs)
    assert len({item["qa_id"] for item in qa}) == len(qa)


def test_attack_cases_cover_five_methods_and_three_positions() -> None:
    cases = read_jsonl(ROOT / "attacks" / "dev" / "cases.jsonl")
    assert len(cases) >= 50
    per_method = Counter(case["attack_method"] for case in cases)
    assert len(per_method) >= 5
    assert min(per_method.values()) >= 10
    for method in per_method:
        positions = {case["position"] for case in cases if case["attack_method"] == method}
        assert positions == {"start", "middle", "end"}, method


def test_dev_and_test_split_groups_are_disjoint() -> None:
    manifest = json.loads((ROOT / "data" / "corpus" / "manifest.json").read_text(encoding="utf-8"))
    dev_groups = {
        entry["split_group"] for entry in manifest["documents"] if entry["split"] == "dev"
    }
    test_groups = {
        entry["split_group"] for entry in manifest["documents"] if entry["split"] == "test"
    }
    assert dev_groups.isdisjoint(test_groups)


def test_attack_cases_use_dev_hosts_only() -> None:
    manifest = json.loads((ROOT / "data" / "corpus" / "manifest.json").read_text(encoding="utf-8"))
    split_by_doc = {entry["doc_id"]: entry["split"] for entry in manifest["documents"]}
    cases = read_jsonl(ROOT / "attacks" / "dev" / "cases.jsonl")
    assert {split_by_doc[case["host_doc_id"]] for case in cases} == {"dev"}


def test_canaries_stay_inside_secret_documents() -> None:
    docs = read_jsonl(ROOT / "data" / "corpus" / "docs.jsonl")
    canaries = json.loads(
        (ROOT / "data" / "secrets" / "canaries.json").read_text(encoding="utf-8")
    )["canaries"]
    contents = {doc["metadata"]["doc_id"]: doc["content"] for doc in docs}
    for canary in canaries:
        carriers = [doc_id for doc_id, text in contents.items() if canary["value"] in text]
        assert carriers == [canary["doc_id"]], canary["canary_id"]

    attack_text = "\n".join(
        case["payload"] for case in read_jsonl(ROOT / "attacks" / "dev" / "cases.jsonl")
    )
    for canary in canaries:
        assert canary["value"] not in attack_text
