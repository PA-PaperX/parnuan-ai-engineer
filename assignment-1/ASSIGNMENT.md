# Parnuan AI Engineer Intern — Take-Home Assignment 1

## Assignment

**Build a Text → Transaction NER System**

Build a system that extracts structured transaction entities from free-form Thai (and mixed Thai/English) text messages. Evaluate it honestly. Recommend which model to ship, and defend your choice.

---

## Overview

Parnuan is an AI-powered personal finance product. One of its core flows is turning a free-form message like `ข้าวมันไก่ 50 น้ำเปล่า 7 แล้วก็ช้อปปิ้ง 500` into structured transactions that the user can review.

This assignment focuses on the **NER layer only**: extracting entities from text. **No categorization. No timestamps. No UI. No storage.**

We care about:

- how you design a dataset
- how you evaluate an LLM system honestly
- how you choose a model under real-world constraints (cost, latency, uptime, rate limits)
- how you make the system **graceful** — it should never crash, never hallucinate fields, never silently drop transactions

---

## Target Schema

Extract one or more transactions from a single message. Each transaction has just two fields:

| Field    | Type   | Notes                                                        |
|----------|--------|--------------------------------------------------------------|
| `amount` | number | The monetary value. Numeric only. Preserve it exactly.       |
| `detail` | string | The "what" — item bought, merchant, service, etc.            |

**Output contract:**

```json
{
  "transactions": [
    { "amount": 50, "detail": "ข้าวมันไก่" },
    { "amount": 7,  "detail": "น้ำเปล่า" }
  ]
}
```

The system **must always return this shape**, even for empty/invalid/non-transaction input (in which case `transactions` is an empty array). Graceful degradation over accuracy.

---

## The Goal

> **Support any input without breaking.**

That does **not** mean 100% accuracy. It means:

1. The system always returns valid structured output matching the contract.
2. Non-transaction messages (`สวัสดี`, `ขอบคุณครับ`) return an empty array, not garbage.
3. Adversarial input (prompt injection, huge input, weird unicode) does not crash the system or leak instructions.
4. If you see an amount in the text, you must preserve it exactly — no rounding, no made-up numbers, no hallucinated transactions.

---

## What You Must Build

### 1. Dataset (≥50 labeled examples)

You can write them yourself, scrape/synthesize them, LLM-generate them, or mix all three — we don't care where the raw text comes from, but **the labels must be correct** and the coverage must be thoughtful.

Your dataset must include at least:

- single-transaction messages
- multi-transaction messages (2+ in one message)
- messages with typos, slang, or mixed Thai/English
- **non-transaction messages** (greetings, questions) — should return empty
- **adversarial** examples (injection attempts, only-amount, only-detail, empty string, huge input)

Store it as JSONL or similar, with each row containing the input text and the expected `transactions` array.

Bonus if you split your dataset into buckets (happy / messy / adversarial) and report metrics per bucket.

### 2. NER System

Build a parser that takes text → structured output matching the schema above.

You decide:

- prompt strategy (few-shot, structured output, function calling, etc.)
- whether to use pure LLM, rules, or a hybrid
- how to handle ambiguous or low-confidence extractions

**Use [OpenRouter](https://openrouter.ai)** for LLM calls. It gives you one API key across many models and makes cost/latency comparison straightforward. Use environment variables for secrets.

### 3. Eval Harness

Write a script that runs your dataset through the system and reports:

- **Field-level precision / recall / F1** (per field: `amount`, `detail`)
- **Exact-match rate** for the full transaction array per message
- **Transaction count accuracy** — did you extract the right *number* of transactions per message?
- **Latency** p50 and p95
- **Cost** per 1k messages (use OpenRouter's pricing)
- **Failure taxonomy** — bucket the errors into types (missed transaction, wrong amount, wrong/truncated detail, hallucinated transaction, merged transactions, etc.). Don't just report a number.

One command should run the eval and print the report.

### 4. Model Recommendation

Compare **at least 2 models** via OpenRouter on your eval. Report:

| Model | F1 | p50 / p95 latency | $/1k messages | Notes |
|-------|----|-------------------|---------------|-------|

**Recommend which one you'd ship** and defend it. "Best" is multi-objective — quality, cost, latency, uptime, rate limits. A candidate who only optimizes F1 is not the candidate we want.

---

## Required Demo Cases

Your eval must include (at minimum) these cases. You can use them directly or equivalents:

1. **Single transaction:** `ข้าวมันไก่ 50`
2. **Multi-transaction:** `ข้าวมันไก่ 50 น้ำเปล่า 7 แล้วก็ช้อปปิ้ง 500`
3. **Non-transaction:** `สวัสดีครับ วันนี้อากาศดี` → empty array
4. **Adversarial:** an input designed to break your system (injection, empty, huge, etc.)

---

## Bonus — Cost Optimization

At 500k+ users × several messages/day, LLM cost is a real constraint.

**Can you reduce cost without hurting F1?** Approaches we'd find interesting:

- regex/rules for the common 80% case → LLM fallback for complex messages
- cheap model → expensive model cascade (route only hard cases to the expensive one)
- prompt caching / batching
- a small local model for pre-filtering

If you attempt this, show the **cost delta and F1 delta** in your eval. A working tiered system that matches single-model F1 at a fraction of the cost is a very strong signal.

This is **optional**. Do it only after the core assignment is solid.

---

## Deliverables

### Part 1 — Dataset

- The labeled dataset file(s)
- A short description of how you built it, what you covered, and what you deliberately left out

### Part 2 — System

- The NER code
- Setup instructions (one command to install, one command to run on a sample input)

### Part 3 — Eval

- The eval script
- The eval report (can be markdown, JSON, or printed output — whatever is readable)

### Part 4 — README

Your README must include:

1. **Approach** — your overall design and why
2. **Dataset** — how you built it, size, coverage, what's missing
3. **Prompt / parsing strategy** — what you tried and what worked
4. **Eval methodology** — metrics, why those metrics, how you define "correct"
5. **Model comparison table** — with F1, latency, cost
6. **Recommendation** — which model you'd ship and why (multi-objective reasoning)
7. **Failure taxonomy** — top failure modes with examples
8. **Graceful degradation** — how your system handles broken/adversarial input
9. **Trade-offs** — what you optimized for, what you sacrificed
10. **Known limitations** — what would likely fail at scale
11. **What you'd improve next** — if you had one more week
12. **Cost optimization** (if attempted) — approach, results, trade-offs
13. **Time spent**

---

## (Bonus) Walkthrough

Include a short walkthrough video (**max 5 minutes**) covering:

1. your dataset design
2. your parsing approach
3. your eval results and failure taxonomy
4. your model recommendation and why
5. current limitations

A simple Loom is enough.

---

## Technical Guidelines

- **Python** preferred, but any language is fine
- **Jupyter Notebook** is encouraged — it's a natural fit for dataset exploration, prompt iteration, and eval reporting in one place
- **[uv](https://github.com/astral-sh/uv)** for dependency management (fast, reproducible, one `pyproject.toml`). A `uv run jupyter lab` setup is ideal.
- Use **OpenRouter** for LLM calls, so we can test out models from many providers quickly
- Use environment variables for secrets — never commit keys
- Keep the solution small and focused.

**Expected time:** 2–4 hours.

This is a guideline, not a hard limit. Scope it yourself. Honest scoping is part of the evaluation.

---

## Evaluation Rubric

| Criteria                          | Weight | What We Look For                                                                       |
|-----------------------------------|--------|----------------------------------------------------------------------------------------|
| Dataset Design                    | 20%    | Coverage, adversarial cases, honest labeling, and thought behind what's included.      |
| Eval Rigor                        | 25%    | Metrics you can defend, failure taxonomy, not just a single number.                    |
| Model Judgment & Cost Awareness   | 20%    | Multi-objective reasoning. Ships-at-scale thinking. Not just "use the biggest model."  |
| Implementation Quality            | 15%    | Graceful degradation. Clean, focused code. Runs with one command.                      |
| Communication                     | 20%    | README clarity, honest trade-offs, clear recommendation.                               |

---

## What We're Looking For

Strong submissions usually show:

- a dataset with real thought behind its coverage
- honest eval numbers with a failure taxonomy
- a model recommendation that weighs cost/latency/uptime, not just F1
- graceful handling of broken and adversarial input
- clear communication of trade-offs

Weak submissions usually:

- skip the dataset and eval on 5 toy examples
- report "accuracy = 0.9" with no breakdown
- pick the biggest model without defending the cost
- crash on empty/adversarial input
- over-engineer with frameworks, classes, and abstractions a script didn't need

---

## Submission Checklist

- [ ] GitHub repository link
- [ ] Dataset (≥50 examples)
- [ ] Working NER system
- [ ] Eval script + report
- [ ] Model comparison with at least 2 models via OpenRouter
- [ ] README with required sections
- [ ] Commit history
- [ ] (bonus) Cost optimization
- [ ] (bonus) Walkthrough video

Good luck. We're excited to see how you think and build.
