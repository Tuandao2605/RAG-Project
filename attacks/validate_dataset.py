"""Kiểm tra cấu trúc và ngữ nghĩa của bộ dữ liệu pilot Sprint 2 (ticket 2.10).

Chạy từ root repo:

    python attacks/validate_dataset.py

Script trả mã 1 nếu có lỗi, và in bảng kiểm kê nhãn để rà trước khi bàn giao.
Kiểm tra cấu trúc dùng JSON Schema; kiểm tra ngữ nghĩa bám theo
``docs/threat_model.md`` và ``docs/dataset_datasheet.md``.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
CORPUS_DOCS = ROOT / "data" / "corpus" / "docs.jsonl"
MANIFEST = ROOT / "data" / "corpus" / "manifest.json"
QA_FILES = (ROOT / "data" / "qa" / "dev.jsonl", ROOT / "data" / "qa" / "test.jsonl")
CANARIES = ROOT / "data" / "secrets" / "canaries.json"
BASE_CASES = ROOT / "attacks" / "base_cases.json"
ATTACK_CASES = ROOT / "attacks" / "dev" / "cases.jsonl"

PRINCIPAL = {"subject_id": "user:an", "groups": ["group:staff"]}
MARKER_RE = re.compile(r"OVERRIDE_ATK_\d{3}")

#: Cặp attack_method → attack_goal được phép. Hai trục tách nhau để một phương
#: thức có thể nhắm nhiều mục tiêu khác nhau.
ALLOWED_METHOD_GOALS = {
    "goal_hijacking": {"answer_contamination"},
    "fake_instruction_role": {"answer_contamination", "availability_degradation"},
    "encoding_obfuscation": {"answer_contamination", "data_exfiltration"},
    "canary_exfiltration": {"data_exfiltration"},
    "forced_refusal": {"availability_degradation"},
}

MIN_DOCS = 20
MIN_QA = 20
MIN_ATTACK_CASES = 50
MIN_CASES_PER_METHOD = 10
MIN_METHODS = 5


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def can_read(principal: dict[str, Any], metadata: dict[str, Any]) -> bool:
    """Công thức quyền đọc v1 trong docs/threat_model.md mục 3."""
    acl = metadata["acl"]
    return bool(
        acl["public"]
        or principal["subject_id"] == metadata["owner"]
        or principal["subject_id"] in acl["readers"]
        or set(principal["groups"]) & set(acl["groups"])
    )


def build_validators() -> dict[str, Draft202012Validator]:
    security = read_json(SCHEMA_DIR / "security_case.schema.json")
    dataset = read_json(SCHEMA_DIR / "rag_dataset.schema.json")
    registry = Registry().with_resources(
        [
            (security["$id"], Resource.from_contents(security)),
            (dataset["$id"], Resource.from_contents(dataset)),
        ]
    )
    return {
        name: Draft202012Validator(
            {"$ref": f"{dataset['$id']}#/$defs/{name}"},
            registry=registry,
            format_checker=FormatChecker(),
        )
        for name in ("document", "qa_item", "attack_case", "corpus_manifest", "canary_registry")
    }


class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return condition

    def schema(self, validator: Draft202012Validator, payload: Any, where: str) -> None:
        for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
            path = "/".join(str(part) for part in error.path) or "<root>"
            self.errors.append(f"{where}: {path}: {error.message}")


def collect() -> dict[str, Any]:
    manifest = read_json(MANIFEST)
    return {
        "manifest": manifest,
        "docs": read_jsonl(CORPUS_DOCS),
        "qa": [item for path in QA_FILES for item in read_jsonl(path)],
        "canaries": read_json(CANARIES),
        "bases": read_json(BASE_CASES)["base_cases"],
        "attacks": read_jsonl(ATTACK_CASES),
    }


def check_documents(audit: Audit, data: dict[str, Any], validators: dict[str, Any]) -> None:
    docs = data["docs"]
    manifest = data["manifest"]
    audit.schema(validators["corpus_manifest"], manifest, "corpus/manifest.json")

    doc_ids = [doc["metadata"]["doc_id"] for doc in docs]
    audit.check(len(doc_ids) == len(set(doc_ids)), "corpus: doc_id bị trùng")
    audit.check(len(docs) >= MIN_DOCS, f"corpus: cần >= {MIN_DOCS} document, hiện có {len(docs)}")

    manifest_ids = [entry["doc_id"] for entry in manifest["documents"]]
    audit.check(len(manifest_ids) == len(set(manifest_ids)), "manifest: doc_id bị trùng")
    audit.check(
        set(manifest_ids) == set(doc_ids),
        "manifest: danh sách doc_id không khớp data/corpus/docs.jsonl",
    )

    groups_by_split: dict[str, set[str]] = defaultdict(set)
    for entry in manifest["documents"]:
        groups_by_split[entry["split"]].add(entry["split_group"])
    audit.check(
        not (groups_by_split["dev"] & groups_by_split["test"]),
        f"split: cùng split_group xuất hiện ở cả dev và test: {groups_by_split['dev'] & groups_by_split['test']}",
    )

    policies = {doc["metadata"]["source_trust"]["policy_version"] for doc in docs}
    audit.check(len(policies) == 1, f"corpus: policy_version không nhất quán: {sorted(policies)}")

    canaries = data["canaries"]
    audit.schema(validators["canary_registry"], canaries, "data/secrets/canaries.json")

    content_by_doc = {doc["metadata"]["doc_id"]: doc["content"] for doc in docs}
    doc_by_id = {doc["metadata"]["doc_id"]: doc for doc in docs}

    for canary in canaries["canaries"]:
        doc = doc_by_id.get(canary["doc_id"])
        if not audit.check(doc is not None, f"canary {canary['canary_id']}: doc_id không tồn tại"):
            continue
        audit.check(
            canary["value"] in doc["content"],
            f"canary {canary['canary_id']}: giá trị không nằm trong nội dung document",
        )
        audit.check(
            doc["metadata"]["sensitivity"] == "secret",
            f"canary {canary['canary_id']}: document chứa canary phải có sensitivity=secret",
        )
        audit.check(
            not doc["metadata"]["acl"]["public"],
            f"canary {canary['canary_id']}: document chứa canary không được public",
        )
        audit.check(
            not can_read(PRINCIPAL, doc["metadata"]),
            f"canary {canary['canary_id']}: principal mẫu không được đọc document canary",
        )
        leaked = [
            other
            for other, text in content_by_doc.items()
            if other != canary["doc_id"] and canary["value"] in text
        ]
        audit.check(not leaked, f"canary {canary['canary_id']}: rò rỉ sang document khác {leaked}")

    for doc in docs:
        metadata = doc["metadata"]
        if metadata["owner"] == "user:attacker":
            audit.check(
                metadata["source_trust"]["level"] == "untrusted",
                f"corpus {metadata['doc_id']}: document attacker kiểm soát phải untrusted",
            )
        audit.check(
            MARKER_RE.search(doc["content"]) is None,
            f"corpus {metadata['doc_id']}: nội dung sạch chứa marker tấn công",
        )


def check_qa(audit: Audit, data: dict[str, Any], validators: dict[str, Any]) -> None:
    qa_items = data["qa"]
    doc_by_id = {doc["metadata"]["doc_id"]: doc for doc in data["docs"]}
    split_by_doc = {entry["doc_id"]: entry["split"] for entry in data["manifest"]["documents"]}
    group_by_doc = {
        entry["doc_id"]: entry["split_group"] for entry in data["manifest"]["documents"]
    }

    qa_ids = [item["qa_id"] for item in qa_items]
    audit.check(len(qa_ids) == len(set(qa_ids)), "qa: qa_id bị trùng")
    audit.check(len(qa_items) >= MIN_QA, f"qa: cần >= {MIN_QA} câu hỏi, hiện có {len(qa_items)}")

    for item in qa_items:
        audit.schema(validators["qa_item"], item, f"qa/{item.get('qa_id', '?')}")
        doc = doc_by_id.get(item["source_doc_id"])
        if not audit.check(doc is not None, f"qa {item['qa_id']}: source_doc_id không tồn tại"):
            continue
        audit.check(
            split_by_doc[item["source_doc_id"]] == item["split"],
            f"qa {item['qa_id']}: split lệch với document nguồn",
        )
        audit.check(
            group_by_doc[item["source_doc_id"]] == item["split_group"],
            f"qa {item['qa_id']}: split_group lệch với document nguồn",
        )
        audit.check(
            item["reference_span"] in doc["content"],
            f"qa {item['qa_id']}: reference_span không phải chuỗi con của document",
        )
        audit.check(
            item["answer"] in item["reference_span"],
            f"qa {item['qa_id']}: answer không nằm trong reference_span",
        )
        audit.check(
            item["answer"] in item["answer_aliases"],
            f"qa {item['qa_id']}: answer phải có mặt trong answer_aliases",
        )
        audit.check(
            can_read(PRINCIPAL, doc["metadata"]),
            f"qa {item['qa_id']}: principal mẫu không đọc được document nguồn",
        )
        for canary in data["canaries"]["canaries"]:
            audit.check(
                canary["value"] not in item["question"] + item["answer"] + item["reference_span"],
                f"qa {item['qa_id']}: câu hỏi/đáp án chứa canary",
            )


def check_attacks(audit: Audit, data: dict[str, Any], validators: dict[str, Any]) -> None:
    attacks = data["attacks"]
    doc_by_id = {doc["metadata"]["doc_id"]: doc for doc in data["docs"]}
    split_by_doc = {entry["doc_id"]: entry["split"] for entry in data["manifest"]["documents"]}
    group_by_doc = {
        entry["doc_id"]: entry["split_group"] for entry in data["manifest"]["documents"]
    }
    base_by_id = {base["base_case_id"]: base for base in data["bases"]}
    canary_by_doc = {item["doc_id"]: item["value"] for item in data["canaries"]["canaries"]}
    clean_payload_space = [doc["content"] for doc in data["docs"]]
    clean_payload_space += [item["question"] + item["answer"] for item in data["qa"]]

    case_ids = [case["case_id"] for case in attacks]
    audit.check(len(case_ids) == len(set(case_ids)), "attack: case_id bị trùng")
    audit.check(
        len(attacks) >= MIN_ATTACK_CASES,
        f"attack: cần >= {MIN_ATTACK_CASES} case dev, hiện có {len(attacks)}",
    )

    methods = {case["attack_method"] for case in attacks}
    audit.check(
        len(methods) >= MIN_METHODS, f"attack: cần >= {MIN_METHODS} nhóm, hiện có {len(methods)}"
    )

    per_method = Counter(case["attack_method"] for case in attacks)
    for method, count in sorted(per_method.items()):
        audit.check(
            count >= MIN_CASES_PER_METHOD,
            f"attack: nhóm {method} cần >= {MIN_CASES_PER_METHOD} case, hiện có {count}",
        )

    positions_by_method: dict[str, set[str]] = defaultdict(set)
    for case in attacks:
        where = f"attack/{case['case_id']}"
        audit.schema(validators["attack_case"], case, where)
        positions_by_method[case["attack_method"]].add(case["position"])

        audit.check(
            case["attack_goal"] in ALLOWED_METHOD_GOALS.get(case["attack_method"], set()),
            f"{where}: cặp attack_method/attack_goal không hợp lệ",
        )
        audit.check(
            case["attack_goal"] == case["objective"]["kind"],
            f"{where}: attack_goal phải trùng objective.kind",
        )

        host = doc_by_id.get(case["host_doc_id"])
        if not audit.check(host is not None, f"{where}: host_doc_id không tồn tại"):
            continue
        audit.check(
            split_by_doc[case["host_doc_id"]] == "dev",
            f"{where}: host document phải thuộc split dev",
        )
        audit.check(
            group_by_doc[case["host_doc_id"]] == case["split_group"],
            f"{where}: split_group lệch với host document",
        )
        audit.check(
            host["metadata"]["owner"] == "user:attacker"
            and host["metadata"]["source_trust"]["level"] == "untrusted",
            f"{where}: host document phải do attacker kiểm soát và untrusted",
        )

        base = base_by_id.get(case["base_case_id"])
        if not audit.check(base is not None, f"{where}: base_case_id không tồn tại"):
            continue
        audit.check(
            case["host_doc_id"] == base["host_doc_id"],
            f"{where}: host_doc_id lệch với base case",
        )
        audit.check(
            case["request"]["query"] == base["query"],
            f"{where}: query lệch với base case",
        )
        audit.check(
            case["task_success"]["answer_contains_all"] == [base["expected_answer"]],
            f"{where}: task_success phải dùng đáp án của base case",
        )
        audit.check(
            case["task_success"]["citation_doc_ids"] == [base["expected_citation"]],
            f"{where}: task_success phải dùng citation của base case",
        )
        citation_doc = doc_by_id.get(base["expected_citation"])
        if citation_doc is not None:
            audit.check(
                can_read(PRINCIPAL, citation_doc["metadata"]),
                f"{where}: principal mẫu không đọc được document citation",
            )

        target_value = case["objective"]["target_value"]
        rules = case["success_rules"]["attack_success"]["any_of"]
        kind = case["objective"]["kind"]

        if kind == "availability_degradation":
            audit.check(
                all("not_contains" in rule for rule in rules),
                f"{where}: availability_degradation phải dùng rule not_contains",
            )
            blocked = {term for rule in rules for term in rule.get("not_contains", [])}
            audit.check(
                set(case["task_success"]["answer_contains_all"]) <= blocked,
                f"{where}: rule not_contains phải chặn mọi đáp án đúng",
            )
        else:
            audit.check(
                all(rule.get("contains") == target_value for rule in rules),
                f"{where}: rule contains phải khớp objective.target_value",
            )

        if kind == "data_exfiltration":
            target_doc_id = case["objective"].get("target_doc_id")
            target_doc = doc_by_id.get(target_doc_id) if target_doc_id else None
            if audit.check(target_doc is not None, f"{where}: target_doc_id không tồn tại"):
                audit.check(
                    target_doc["metadata"]["sensitivity"] == "secret",
                    f"{where}: document đích phải là secret",
                )
                audit.check(
                    not can_read(PRINCIPAL, target_doc["metadata"]),
                    f"{where}: principal mẫu không được đọc document đích",
                )
                audit.check(
                    canary_by_doc.get(target_doc_id) == target_value,
                    f"{where}: target_value phải là canary của document đích",
                )
            audit.check(
                target_value not in case["payload"],
                f"{where}: payload không được chứa canary (attacker không biết trước)",
            )
        elif kind == "answer_contamination":
            audit.check(
                MARKER_RE.fullmatch(target_value) is not None
                and target_value not in "".join(clean_payload_space),
                f"{where}: marker phải là marker riêng, không có trong dữ liệu sạch",
            )
        else:
            audit.check(
                target_value == base["expected_answer"],
                f"{where}: target_value của availability_degradation phải là đáp án đúng",
            )

    for method, positions in sorted(positions_by_method.items()):
        audit.check(
            positions == {"start", "middle", "end"},
            f"attack: nhóm {method} chưa phủ đủ 3 vị trí, hiện có {sorted(positions)}",
        )


def print_audit(data: dict[str, Any]) -> None:
    attacks = data["attacks"]
    print(f"Documents: {len(data['docs'])} | QA: {len(data['qa'])} | Attack case: {len(attacks)}")
    print()
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    positions: dict[str, Counter[str]] = defaultdict(Counter)
    for case in attacks:
        matrix[case["attack_method"]][case["attack_goal"]] += 1
        positions[case["attack_method"]][case["position"]] += 1
    goals = sorted({goal for counter in matrix.values() for goal in counter})
    header = f"{'method':22}" + "".join(f"{goal[:22]:24}" for goal in goals) + "start/middle/end"
    print(header)
    for method in sorted(matrix):
        row = f"{method:22}" + "".join(f"{matrix[method][goal]:<24}" for goal in goals)
        row += "/".join(str(positions[method][pos]) for pos in ("start", "middle", "end"))
        print(row)
    print()
    print("Case theo base case:", dict(sorted(Counter(c["base_case_id"] for c in attacks).items())))
    print("Case theo host doc: ", dict(sorted(Counter(c["host_doc_id"] for c in attacks).items())))
    split_counts = Counter(entry["split"] for entry in data["manifest"]["documents"])
    print("Document theo split:", dict(sorted(split_counts.items())))
    print(
        "QA theo split:      ", dict(sorted(Counter(item["split"] for item in data["qa"]).items()))
    )


def main() -> int:
    validators = build_validators()
    for name, schema in (
        ("security_case", SCHEMA_DIR / "security_case.schema.json"),
        ("rag_dataset", SCHEMA_DIR / "rag_dataset.schema.json"),
    ):
        Draft202012Validator.check_schema(read_json(schema))
        print(f"Schema hợp lệ: {name}")

    data = collect()
    audit = Audit()
    for document in data["docs"]:
        audit.schema(
            validators["document"],
            document,
            f"corpus/{document.get('metadata', {}).get('doc_id', '?')}",
        )

    check_documents(audit, data, validators)
    check_qa(audit, data, validators)
    check_attacks(audit, data, validators)

    print()
    print_audit(data)
    print()
    if audit.errors:
        print(f"LỖI ({len(audit.errors)}):")
        for message in audit.errors:
            print(f"  - {message}")
        return 1
    print("OK: toàn bộ kiểm tra cấu trúc và ngữ nghĩa đều đạt.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
