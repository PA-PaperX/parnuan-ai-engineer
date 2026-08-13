"""The public output contract for the transaction extractor."""

from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Transaction(BaseModel):
    """One extracted transaction."""

    model_config = ConfigDict(extra="forbid", strict=True)

    amount: float = Field(description="The monetary amount copied from the input.")
    detail: str = Field(description="The item, merchant, or service being paid for.")

    @field_validator("amount")
    @classmethod
    def amount_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("amount must be finite")
        return value

    @field_validator("detail")
    @classmethod
    def detail_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("detail must not be blank")
        return value.strip()


class ExtractionResponse(BaseModel):
    """The only response shape exposed by the application."""

    model_config = ConfigDict(extra="forbid", strict=True)

    transactions: list[Transaction] = Field(default_factory=list)


def empty_response() -> ExtractionResponse:
    """Return a safe response for empty, invalid, or unsupported input."""

    return ExtractionResponse(transactions=[])

