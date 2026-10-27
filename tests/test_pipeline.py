import io
import unittest
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from app.main import app, process_document
from app.schemas import (
    BillData,
    BillExtractionResponse,
    BillItem,
    PagewiseLineItems,
    TokenUsage,
)


def png_bytes() -> bytes:
    image = Image.new("RGB", (400, 160), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class PipelineTests(unittest.TestCase):
    @patch("app.main.BillExtractor")
    @patch("app.main.OCREngine.extract_text", return_value="Consultation 100 x 2 200")
    def test_image_pipeline_returns_typed_items_and_usage(
        self, _ocr, extractor_type
    ) -> None:
        extractor = extractor_type.return_value
        extractor.extract_from_text.return_value = PagewiseLineItems(
            page_no=1,
            page_type="Bill Detail",
            bill_items=[
                BillItem(
                    item_name="Consultation",
                    item_amount=200,
                    item_rate=100,
                    item_quantity=2,
                )
            ],
        )
        extractor.get_token_usage.return_value = {
            "total_tokens": 25,
            "input_tokens": 15,
            "output_tokens": 10,
        }

        response = process_document(png_bytes())

        self.assertTrue(response.is_success)
        self.assertEqual(response.data.total_item_count, 1)
        self.assertEqual(response.data.pagewise_line_items[0].page_no, 1)
        self.assertEqual(response.token_usage.total_tokens, 25)
        extractor.extract_from_text.assert_called_once()

    def test_health_endpoint_is_live(self) -> None:
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_upload_returns_response_model_shape(self) -> None:
        result = BillExtractionResponse(
            is_success=True,
            token_usage=TokenUsage(total_tokens=5, input_tokens=3, output_tokens=2),
            data=BillData(
                pagewise_line_items=[
                    PagewiseLineItems(
                        page_no=1,
                        page_type="Bill Detail",
                        bill_items=[
                            BillItem(
                                item_name="Consultation",
                                item_amount=100,
                                item_rate=100,
                                item_quantity=1,
                            )
                        ],
                    )
                ],
                total_item_count=1,
            ),
        )
        with patch("app.main.process_document", return_value=result):
            response = TestClient(app).post(
                "/extract-bill-data",
                files={"file": ("bill.png", png_bytes(), "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["pagewise_line_items"][0]["page_no"], 1)
        self.assertEqual(body["token_usage"]["total_tokens"], 5)

    def test_unsupported_upload_returns_client_error(self) -> None:
        response = TestClient(app).post(
            "/extract-bill-data",
            files={"file": ("bill.txt", b"not a bill image", "text/plain")},
        )

        self.assertEqual(response.status_code, 415)

    def test_empty_upload_returns_client_error(self) -> None:
        response = TestClient(app).post(
            "/extract-bill-data",
            files={"file": ("empty.png", b"", "image/png")},
        )

        self.assertEqual(response.status_code, 400)

    @patch("app.main.settings")
    def test_upload_size_limit_is_enforced(self, settings) -> None:
        settings.max_file_size_bytes = 4
        settings.max_file_size_mb = 1
        response = TestClient(app).post(
            "/extract-bill-data",
            files={"file": ("large.png", b"12345", "image/png")},
        )

        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main()
