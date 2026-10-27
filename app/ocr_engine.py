import io

import pytesseract
from PIL import Image, UnidentifiedImageError


class OCRServiceError(RuntimeError):
    """Raised when the local Tesseract OCR service cannot process a page."""


class OCREngine:
    """Thin adapter around the Tesseract command-line OCR engine."""

    @staticmethod
    def extract_text(image_bytes: bytes) -> str:
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                return pytesseract.image_to_string(image, config="--oem 3 --psm 6")
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRServiceError(
                "Tesseract is not installed or is not available on PATH"
            ) from exc
        except (pytesseract.TesseractError, UnidentifiedImageError, OSError) as exc:
            raise OCRServiceError("Tesseract could not read the page image") from exc
