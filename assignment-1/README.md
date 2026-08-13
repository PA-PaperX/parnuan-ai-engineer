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

## Local demo UI

The core is still a Python package and CLI because those interfaces are easiest to test and
benchmark. I also added a small local web demo for reviewers and non-technical users. It uses a
receipt-like layout with readable text, sample inputs, visible status, model, and latency. The UI
does not contain extraction logic; it calls the same parser used by the CLI and evaluator.

Start it with:

```powershell
uv run python -m transaction_ner.web
```

Then open `http://127.0.0.1:8765`. To verify the layout without sending a model request:

```powershell
uv run python -m transaction_ner.web --offline
```

The demo is local, but a normal run still sends the text to OpenRouter. Do not enter real personal
financial data. The server does not store messages and does not log request bodies.

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
  --models "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free" `
  --output eval/eval_report.json `
  --output-md eval/eval_report.md
```

Use `--limit 5` for a small smoke test. The report exports to `eval/eval_report.json` and `eval/eval_report.md`, including:

- amount and detail micro precision, recall, and F1 using multiset field matching;
- full ordered transaction-array exact match;
- transaction-count accuracy;
- p50 and p95 latency;
- cost per 1,000 messages when OpenRouter returns usage cost;
- status counts and failure taxonomy: missed, hallucinated, merged, extra, wrong amount, wrong/truncated detail, and rate_limited;
- exact-match rate by dataset bucket.

The committed submission evidence is saved in [`eval/eval_report.json`](file:///c:/Users/Administrator/Desktop/train/parnuan-engineer-dev/assignment-1/eval/eval_report.json) and [`eval/eval_report.md`](file:///c:/Users/Administrator/Desktop/train/parnuan-engineer-dev/assignment-1/eval/eval_report.md).

## Model recommendation

### Live Benchmark Results (80 Examples)

| Model | Amount F1 | Detail F1 | Exact Match | Count Accuracy | p50 / p95 Latency (ms) | $/1k Msgs | Status Breakdown |
|---|---:|---:|---:|---:|---:|---:|---|
| **`google/gemma-4-26b-a4b-it:free`** | **0.976** | **0.784** | **81.25%** | **96.25%** | 3,401.9 / 15,349.3 | $0.00 | `ok: 70`, `input_empty: 3`, `rate_limited: 7` |
| **`google/gemma-4-31b-it:free`** | 0.197 | 0.169 | 40.00% | 41.25% | 15,165.6 / 17,029.6 | $0.00 | `rate_limited: 68`, `ok: 9`, `input_empty: 3` |

### Analysis & Recommendation

- **Recommended Production Candidate:** **`google/gemma-4-26b-a4b-it:free`**
  - **Precision & Accuracy:** High amount extraction precision (1.00) and F1 (0.976) with 96.25% transaction count accuracy.
  - **Bucket Breakdown:** Achieved 100% exact match on `non_transaction`, 86.7% on `adversarial`, 76.0% on `messy`, and 72.0% on `happy`.
  - **Latency & Availability:** Fast median latency (p50: ~3.4s) with minimal provider rate limiting (only 7 HTTP 429 encountered out of 80 requests).
  - **Failure Taxonomy:** Main failure mode is minor whitespace/formatting truncation in details (`wrong_or_truncated_detail: 12`) and 1 missed transaction.
- **Evaluation Note on `google/gemma-4-31b-it:free`:**
  - Under high shared free-tier load on OpenRouter, the 31B provider node experienced heavy rate limiting (68/80 requests returned `rate_limited` despite exponential backoff). The low benchmark score reflects provider-side availability limits on the free tier rather than underlying model language capability, rendering 31B **inconclusive** for free shared production deployment.

## Known limitations and next steps

- Full live benchmark evaluation has been completed and evidence is committed in `eval/eval_report.json` and `eval/eval_report.md`.
- All temporary evaluation API keys have been revoked following the benchmark run to ensure zero active secrets in the repository.
- Exponential backoff (2s, 4s, 8s) is implemented in `client.py` for handling HTTP 429 rate limits.
- Next steps for production: add a deterministic rule-based fast path, local response caching, request concurrency, and human review for low-confidence detail extractions.

## Time spent

The work was completed incrementally across 6 main areas (total ~4.5 hours):

- **Contract and project setup:** 30 minutes (Pydantic schema, package boundaries, pytest contract suite)
- **Dataset design and validation:** 45 minutes (80 synthetic Thai/mixed examples across 4 buckets)
- **OpenRouter integration:** 60 minutes (Client adapter, JSON mode handling, prompt boundaries, error mapping)
- **Evaluation harness & backoff:** 60 minutes (Multiset metrics, failure taxonomy, exponential backoff, JSON/MD CLI exports)
- **Testing and documentation:** 45 minutes (13 test cases passing, ruff linting, docstrings, README setup)
- **Benchmark and report execution:** 30 minutes (Live 80-example x 2 model run, metrics collection, security key rotation)

