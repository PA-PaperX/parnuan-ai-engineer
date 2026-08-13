# Assignment 1 — Thai Text → Transaction NER

Status: contract scaffold. The first commit intentionally does not call an LLM.

## Goal

Extract one or more transactions from Thai or mixed Thai/English text:

```json
{
  "transactions": [
    {"amount": 50, "detail": "ข้าวมันไก่"}
  ]
}
```

The application must return this shape for every input, including empty and invalid input.

## Development commands

```powershell
uv sync
uv run pytest -q
uv run python -m transaction_ner.cli "ข้าวมันไก่ 50"
```

The current scaffold returns an empty list by design. The next commit adds the labeled dataset;
the model provider is added only after the contract and labels are testable.

## Design rule

The provider will be isolated behind a small interface. Parsing, validation, evaluation, and the
CLI should not need to know whether the response came from OpenRouter or a local fixture.

