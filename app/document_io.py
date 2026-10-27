import io
import warnings
from typing import Literal

from PIL import Image, UnidentifiedImageError
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFPopplerTimeoutError,
    PDFSyntaxError,
)


DocumentType = Literal["pdf", "image"]


class DocumentError(ValueError):
    """Base error for invalid or unsupported document inputs."""


class EmptyDocumentError(DocumentError):
    """Raised when an upload has no content."""


class UnsupportedDocumentError(DocumentError):
    """Raised when an upload is not a supported PDF or image."""


class InvalidDocumentError(DocumentError):
    """Raised when document bytes cannot be decoded."""


class DocumentSizeLimitError(DocumentError):
    """Raised when a document exceeds a configured size or page limit."""


class DocumentConversionError(RuntimeError):
    """Raised when a supported PDF cannot be rendered."""


class DocumentUtils:
    """Document signature validation and PDF page conversion."""

    _IMAGE_SIGNATURES = (
        b"\xFF\xD8\xFF",
        b"\x89PNG\r\n\x1a\n",
        b"GIF87a",
        b"GIF89a",
        b"BM",
        b"II*\x00",
        b"MM\x00*",
        b"RIFF",
    )
    _SUPPORTED_IMAGE_FORMATS = {
        "JPEG",
        "PNG",
        "GIF",
        "BMP",
        "TIFF",
        "WEBP",
    }
    _MAX_IMAGE_PIXELS = 40_000_000

    @classmethod
    def detect_document_type(cls, content: bytes) -> DocumentType:
        if not content:
            raise EmptyDocumentError("The uploaded document is empty")
        if content.startswith(b"%PDF-"):
            return "pdf"
        if content.startswith(cls._IMAGE_SIGNATURES):
            cls.validate_image(content)
            return "image"
        raise UnsupportedDocumentError("Only PDF and supported image files are accepted")

    @classmethod
    def validate_image(cls, content: bytes) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.format not in cls._SUPPORTED_IMAGE_FORMATS:
                        raise UnsupportedDocumentError(
                            f"Unsupported image format: {image.format or 'unknown'}"
                        )
                    if image.width * image.height > cls._MAX_IMAGE_PIXELS:
                        raise DocumentSizeLimitError(
                            "Image dimensions exceed the 40-megapixel limit"
                        )
                    image.verify()
        except DocumentSizeLimitError:
            raise
        except UnsupportedDocumentError:
            raise
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise InvalidDocumentError("The uploaded image is invalid or unreadable") from exc

    @staticmethod
    def pdf_to_images(
        pdf_bytes: bytes,
        dpi: int = 300,
        max_pages: int = 50,
    ) -> list[bytes]:
        try:
            info = pdfinfo_from_bytes(pdf_bytes)
            page_count = int(info["Pages"])
            if page_count > max_pages:
                raise DocumentSizeLimitError(
                    f"PDF contains {page_count} pages; the limit is {max_pages}"
                )
            if page_count < 1:
                raise InvalidDocumentError("The PDF contains no pages")

            images = convert_from_bytes(pdf_bytes, dpi=dpi)
        except DocumentSizeLimitError:
            raise
        except (PDFInfoNotInstalledError, PDFPopplerTimeoutError) as exc:
            raise DocumentConversionError(
                "PDF rendering failed; verify that Poppler is installed and the PDF is valid"
            ) from exc
        except (PDFPageCountError, PDFSyntaxError) as exc:
            raise InvalidDocumentError("The uploaded PDF is invalid or unreadable") from exc

        pages: list[bytes] = []
        for image in images:
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            pages.append(buffer.getvalue())
        return pages
