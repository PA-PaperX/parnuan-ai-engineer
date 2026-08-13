"""Input boundary for extraction.

The model provider will be added after this contract is tested. Keeping this
function small makes the provider replaceable and the fallback behavior clear.
"""

from .schema import ExtractionResponse, empty_response


def extract(text: str | None) -> ExtractionResponse:
    """Return a valid response for every input.

    This first commit intentionally has no model call. It establishes the
    graceful-degradation contract before adding network behavior.
    """

    if not isinstance(text, str) or not text.strip():
        return empty_response()
    return empty_response()

