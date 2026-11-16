"""Defense hooks dùng chung cho baseline và các phiên bản có phòng vệ."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

Context = dict[str, str | float]


class ContextDefense(Protocol):
    """Giao diện defense nằm giữa retrieval và prompt builder."""

    name: str

    def apply(self, question: str, contexts: list[Context]) -> list[Context]: ...


class BaselineDefense:
    """B0: giữ nguyên context trước khi tạo prompt baseline."""

    name = "b0"

    def apply(self, question: str, contexts: list[Context]) -> list[Context]:
        return [dict(context) for context in contexts]


class SandwichDefense(BaselineDefense):
    """B1: giữ nguyên context và chọn prompt Sandwich ở pipeline."""

    name = "b1"


def create_defense(name: str) -> ContextDefense:
    """Tạo hook defense theo ID benchmark."""
    if name == "b0":
        return BaselineDefense()
    if name == "b1":
        return SandwichDefense()
    raise ValueError(f"Unknown defense {name!r}. Available defenses: b0, b1.")


def public_context(context: Mapping[str, object]) -> Context:
    """Chuẩn hóa context trước khi ghi trace hoặc đưa vào prompt."""
    result: Context = {}
    for key in ("chunk_id", "doc_id", "text", "score"):
        value = context.get(key)
        if isinstance(value, str):
            result[key] = value
        elif isinstance(value, (float, int)):
            result[key] = float(value)
    return result
