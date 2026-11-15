from rag.prompting import build_prompt


def test_grounded_prompt_contains_question_context_and_source() -> None:
    prompt = build_prompt(
        "Mật khẩu cần dài bao nhiêu?",
        [
            {
                "chunk_id": "policy:0000",
                "doc_id": "policy",
                "text": "Mật khẩu phải có ít nhất 12 ký tự.",
            }
        ],
    )

    assert "Mật khẩu cần dài bao nhiêu?" in prompt
    assert "Mật khẩu phải có ít nhất 12 ký tự." in prompt
    assert "policy:0000" in prompt
    assert "không phải chỉ dẫn" in prompt
