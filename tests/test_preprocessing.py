import io
import unittest

from PIL import Image, ImageDraw

from app.document_io import InvalidDocumentError
from app.preprocessing import DocumentPreprocessor


class PreprocessingTests(unittest.TestCase):
    def test_enhances_image_and_returns_png(self) -> None:
        image = Image.new("RGB", (400, 160), "white")
        ImageDraw.Draw(image).text((20, 50), "MEDICAL BILL 123.45", fill="black")
        source = io.BytesIO()
        image.save(source, format="PNG")

        result = DocumentPreprocessor.enhance_image(source.getvalue())

        with Image.open(io.BytesIO(result)) as processed:
            self.assertEqual(processed.format, "PNG")
            self.assertEqual(processed.mode, "L")
            self.assertEqual(processed.size, image.size)

    def test_rejects_invalid_page_bytes(self) -> None:
        with self.assertRaises(InvalidDocumentError):
            DocumentPreprocessor.enhance_image(b"invalid image")


if __name__ == "__main__":
    unittest.main()
