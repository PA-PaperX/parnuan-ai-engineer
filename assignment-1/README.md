# Assignment 1 — Thai Text → Transaction NER

This repository contains an intentionally small, explainable NER service for extracting
financial transactions from Thai or mixed Thai/English text. It returns only:

```json
{"transactions": [{"amount": 50, "detail": "ข้าวมันไก่"}]}
```

The service is designed around one rule: a broken provider response must never break the
public contract. Empty, oversized, invalid, or unsupported input returns
`{"transactions": []}`.

## Development history

The work is split into reviewable branches and commits:

1. `assignment-1/contract-scaffold` — schema, CLI boundary, package setup, and contract tests.
2. `assignment-1/dataset-validation` — 80 labeled synthetic Thai examples and dataset checks.
3. `assignment-1/openrouter-provider` — OpenRouter adapter, prompt boundary, JSON parsing, and fallback tests.
4. `assignment-1/evaluation` — field metrics, latency/cost collection, and failure taxonomy.

The branch names describe the product change rather than the coding tool used to create it.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run pytest -q
uv run ruff check .
uv run ty check
```

For an offline contract check:

```powershell
uv run python -m transaction_ner.cli --offline "ข้าวมันไก่ 50"
```

For OpenRouter, set the key only in the shell or user environment. Never put it in this
repository:

```powershell
$env:OPENROUTER_API_KEY = "<new-key>"
$env:MODEL_NAME = "google/gemma-4-31b-it:free"
uv run python -m transaction_ner.cli "ข้าวมันไก่ 50"
```

The client requests JSON mode, temperature 0, a bounded input, and
`provider.data_collection=deny` by default. OpenRouter/provider policies still apply because
the call is remote; use synthetic examples for evaluation and revoke exposed keys.

## Approach

The implementation has four narrow layers:

- `schema.py` defines the only public output contract with strict Pydantic validation.
- `prompts.py` places user text inside an `<input>` data boundary and asks for JSON only.
- `client.py` translates one OpenRouter response into a small provider-neutral result object.
- `parser.py` bounds input, parses JSON/fenced JSON, validates every field, and falls back to an
  empty response on provider or parsing failure.

This is deliberately an LLM-first baseline, not a hidden rule system. That makes model quality
measurable and keeps the provider replaceable. A production version could add a cheap rule-based
fast path after measuring whether it preserves recall.

## Dataset

`dataset/examples.jsonl` contains 80 synthetic, hand-reviewed examples:

| Bucket | Count | Coverage |
|---|---:|---|
| happy | 25 | clear single and multi-transaction messages |
| messy | 25 | typos, slang, mixed English, and inconsistent spacing |
| non_transaction | 15 | greetings, questions, and ordinary conversation |
| adversarial | 15 | prompt injection, missing fields, huge input, and unusual text |

The labels deliberately exclude categorization, timestamps, currencies, and personal data. The
dataset is a development fixture, not a representative production corpus; real anonymized data
would be needed before launch.

Validate it with:

```powershell
uv run python -m transaction_ner.dataset
```

## Evaluation

Run two free OpenRouter candidates serially:

```powershell
uv run python -m transaction_ner.eval `
  --models "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free"
```

Use `--limit 5` for a small smoke test. The report includes:

- amount and detail micro precision, recall, and F1 using multiset field matching;
- full ordered transaction-array exact match;
- transaction-count accuracy;
- p50 and p95 latency;
- cost per 1,000 messages when OpenRouter returns usage cost;
- status counts and failure taxonomy: missed, hallucinated, merged, extra, wrong amount, and
  wrong/truncated detail;
- exact-match rate by dataset bucket.

The evaluator does not write raw prompts or model outputs to disk. A model comparison should be
recorded only after a live run with a valid, rotated key, for example in `eval/results/` (ignored
by Git).

## Model recommendation

The default candidate is `google/gemma-4-31b-it:free` because it is the requested no-cost Thai
baseline and is likely to be more capable on messy multi-transaction text than a smaller model.
That is a hypothesis, not a fabricated benchmark result. The ship decision must use the generated
table: choose the candidate that meets the required F1 and graceful-degradation behavior while
having acceptable p95 latency, availability, and cost. If the smaller free model is close in F1,
it is the better scale choice; if it materially merges or hallucinates transactions, use 31B.

## Known limitations and next steps

- No live benchmark numbers are committed until the exposed API key is revoked and a new key is
  supplied; this avoids presenting an unrepeatable or unsafe result as evidence.
- Free endpoints can have rate limits, changing availability, and provider-specific privacy
  behavior.
- The current parser does not use a local deterministic fast path, retry policy, or concurrency.
- Detail matching is normalized for whitespace/case, while amount matching remains exact.
- One more week would add a rules-first cascade, retry/backoff with a request budget, a larger
  anonymized validation set, provider availability monitoring, and human review for low-confidence
  outputs.

## Time spent

The implementation is intentionally incremental; the final time and live benchmark notes should
be filled in after the last evaluation run.
