# B1 Sandwich Prompting (ticket 2.7)

`defenses/sandwich.py` exposes `build_prompt(question, chunks, defense_id)` and
the two stable IDs `b0` and `b1`. The RAG CLI uses the same retrieval call and
same returned chunk objects for either ID; it changes only the prompt passed to
the configured chat client.

## Prompt variants

- **B0** uses one task instruction, retrieved context, then the question.
- **B1** places the same task and untrusted-context boundary instruction before
  and after the retrieved context, with the same question repeated after the
  context. This is the sandwich intervention.

Both variants include the retrieved chunk IDs, document IDs and text. No attack
labels, objective values, success rules, or evaluator outputs are accepted by
the prompt builder. Empty or malformed input fails explicitly rather than
silently changing the experiment.

## Reproducible CLI configuration

```bash
python -m rag.cli answer \
  --index artifacts/index \
  --question "Question text" \
  --top-k 3 \
  --defense b1 \
  --temperature 0 \
  --seed 42
```

Use `--defense b0` for the baseline, keeping the index, question, `top-k`,
provider, model, temperature and seed fixed. The prompt builder does not add a
detector; detector FPR therefore remains `N/A` for B0/B1. The CLI response
includes the same retrieved sources alongside the generated answer.

## Offline checks

`tests/test_sandwich.py` samples one dev case from each of the five attack
methods and verifies the retrieved payload/question are preserved while B1
wraps context with the boundary instruction. It also checks the CLI hook and
invalid configuration handling without calling a model. Provider client tests
check temperature/seed forwarding for both Ollama and OpenAI-compatible APIs.

This prompt-only defense is a pilot baseline, not an ACL or output-security
boundary. Retrieved-content trust decisions and access control remain separate
responsibilities in the RAG pipeline.
