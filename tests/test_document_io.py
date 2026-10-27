import io
import unittest

from PIL import Image

from app.document_io import (
    DocumentUtils,
    EmptyDocumentError,
    InvalidDocumentError,
    UnsupportedDocumentError,
)


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


class DocumentIOTests(unittest.TestCase):
    def test_detects_pdf_and_image_signatures(self) -> None:
        self.assertEqual(DocumentUtils.detect_document_type(b"%PDF-1.7 data"), "pdf")
        self.assertEqual(DocumentUtils.detect_document_type(png_bytes()), "image")

    def test_rejects_empty_and_unsupported_documents(self) -> None:
        with self.assertRaises(EmptyDocumentError):
            DocumentUtils.detect_document_type(b"")
        with self.assertRaises(UnsupportedDocumentError):
            DocumentUtils.detect_document_type(b"not a document")

    def test_rejects_corrupt_image_with_valid_signature(self) -> None:
        with self.assertRaises(InvalidDocumentError):
            DocumentUtils.detect_document_type(b"\x89PNG\r\n\x1a\ncorrupt")


if __name__ == "__main__":
    unittest.main()
