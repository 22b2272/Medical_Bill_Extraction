import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.extraction import BillExtractor, ExtractionError


class BillExtractorTests(unittest.TestCase):
    @patch("app.extraction.settings")
    @patch("app.extraction.anthropic.Anthropic")
    def test_parses_typed_response_and_accumulates_usage(
        self, anthropic_client, settings
    ) -> None:
        settings.anthropic_api_key = "test-key"
        settings.anthropic_model = "test-model"
        settings.max_tokens = 256
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(
                    text=json.dumps(
                        {
                            "page_no": 99,
                            "page_type": "Bill Detail",
                            "bill_items": [
                                {
                                    "item_name": "Consultation",
                                    "item_amount": 200,
                                    "item_rate": 100,
                                    "item_quantity": 2,
                                }
                            ],
                        }
                    )
                )
            ],
            usage=SimpleNamespace(input_tokens=20, output_tokens=10),
        )
        anthropic_client.return_value = client
        extractor = BillExtractor()

        result = extractor.extract_from_text("Consultation 100 x 2 200", 1)

        self.assertEqual(result.page_no, 1)
        self.assertEqual(result.bill_items[0].item_amount, 200)
        self.assertEqual(
            extractor.get_token_usage(),
            {"total_tokens": 30, "input_tokens": 20, "output_tokens": 10},
        )
        client.messages.create.assert_called_once()

    @patch("app.extraction.settings")
    @patch("app.extraction.anthropic.Anthropic")
    def test_rejects_invalid_provider_json(self, anthropic_client, settings) -> None:
        settings.anthropic_api_key = "test-key"
        settings.anthropic_model = "test-model"
        settings.max_tokens = 256
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="not json")],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )
        anthropic_client.return_value = client

        with self.assertRaises(ExtractionError):
            BillExtractor().extract_from_text("OCR text", 1)


if __name__ == "__main__":
    unittest.main()
