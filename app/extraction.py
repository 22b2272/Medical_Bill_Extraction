import json

import anthropic
from pydantic import ValidationError

from .config import settings
from .schemas import PagewiseLineItems


class ExtractionConfigurationError(RuntimeError):
    """Raised when required LLM configuration is missing."""


class ExtractionError(RuntimeError):
    """Raised when the LLM request or structured extraction fails."""


class BillExtractor:
    """Extract typed bill line items from one page of OCR text."""

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise ExtractionConfigurationError(
                "ANTHROPIC_API_KEY must be configured for bill extraction"
            )
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def extract_from_text(self, ocr_text: str, page_number: int) -> PagewiseLineItems:
        prompt = f"""Extract the line items visible in this medical bill page.
Do not invent unreadable values. Do not treat subtotals or totals as line items.
Return only JSON matching this shape:
{{
  "page_no": {page_number},
  "page_type": "Bill Detail",
  "bill_items": [
    {{
      "item_name": "exact item name",
      "item_amount": 0.00,
      "item_rate": 0.00,
      "item_quantity": 0.00
    }}
  ]
}}
page_type must be exactly one of "Bill Detail", "Final Bill", or "Pharmacy".

OCR text for page {page_number}:
{ocr_text}"""

        try:
            message = self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise ExtractionError("The Anthropic extraction request failed") from exc

        self.input_tokens += message.usage.input_tokens
        self.output_tokens += message.usage.output_tokens
        self.total_tokens += message.usage.input_tokens + message.usage.output_tokens

        response_text = next(
            (block.text for block in message.content if hasattr(block, "text")),
            None,
        )
        if not response_text:
            raise ExtractionError("The extraction provider returned no text")

        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            parsed = json.loads(response_text)
            if not isinstance(parsed, dict):
                raise TypeError("Expected a JSON object")
            parsed["page_no"] = page_number
            return PagewiseLineItems.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise ExtractionError(
                "The extraction provider returned invalid structured data"
            ) from exc

    def get_token_usage(self) -> dict[str, int]:
        return {
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
