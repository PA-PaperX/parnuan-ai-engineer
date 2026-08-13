# Evaluation Report Evidence

- **Timestamp**: `2026-08-13T19:29:14.016580+00:00`
- **Git Commit**: `7354d335eb6fdfb4bb57e1aa0599551dc18592cf`
- **Dataset Size**: 80 examples
- **Rate Limit Count**: 75

| Model | Amount F1 | Detail F1 | Exact match | Count accuracy | p50/p95 ms | $/1k |
|---|---:|---:|---:|---:|---:|---:|
| google/gemma-4-31b-it:free | 0.197 | 0.169 | 0.400 | 0.412 | 15165.6/17029.6 | $0.000000 |
| google/gemma-4-26b-a4b-it:free | 0.976 | 0.784 | 0.812 | 0.963 | 3401.9/15349.3 | $0.000000 |

### google/gemma-4-31b-it:free
Status counts: `{"rate_limited": 68, "ok": 9, "input_empty": 3}`
Failure taxonomy: `{"rate_limited": 47, "correct": 32, "wrong_or_truncated_detail": 1}`
Exact match by bucket: `{"adversarial": 0.8, "happy": 0.12, "messy": 0.08, "non_transaction": 1.0}`

### google/gemma-4-26b-a4b-it:free
Status counts: `{"ok": 70, "input_empty": 3, "rate_limited": 7}`
Failure taxonomy: `{"correct": 65, "missed_transaction": 1, "wrong_or_truncated_detail": 12, "rate_limited": 2}`
Exact match by bucket: `{"adversarial": 0.8666666666666667, "happy": 0.72, "messy": 0.76, "non_transaction": 1.0}`
