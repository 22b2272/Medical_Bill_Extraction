import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import settings
from .document_io import (
    DocumentConversionError,
    DocumentSizeLimitError,
    DocumentUtils,
    EmptyDocumentError,
    InvalidDocumentError,
    UnsupportedDocumentError,
)
from .extraction import BillExtractor, ExtractionConfigurationError, ExtractionError
from .ocr_engine import OCRServiceError, OCREngine
from .preprocessing import DocumentPreprocessor
from .schemas import (
    BillData,
    BillExtractionResponse,
    HealthResponse,
    PagewiseLineItems,
    TokenUsage,
)
from .validation import BillValidator


logger = logging.getLogger(__name__)
app = FastAPI(title="Medical Bill Extraction API", version=__version__)


def process_document(content: bytes) -> BillExtractionResponse:
    if len(content) > settings.max_file_size_bytes:
        raise DocumentSizeLimitError(
            f"Document exceeds the {settings.max_file_size_mb} MB upload limit"
        )

    document_type = DocumentUtils.detect_document_type(content)
    if document_type == "pdf":
        page_images = DocumentUtils.pdf_to_images(
            content,
            dpi=settings.default_dpi,
            max_pages=settings.max_pages,
        )
    else:
        page_images = [content]

    if len(page_images) > settings.max_pages:
        raise DocumentSizeLimitError(
            f"Document exceeds the {settings.max_pages}-page limit"
        )

    extractor = BillExtractor()
    pages: list[PagewiseLineItems] = []
    for page_number, image_bytes in enumerate(page_images, start=1):
        processed_image = DocumentPreprocessor.enhance_image(image_bytes)
        ocr_text = OCREngine.extract_text(processed_image)
        if not ocr_text.strip():
            raise OCRServiceError(f"No text could be recognized on page {page_number}")

        page = extractor.extract_from_text(ocr_text, page_number)
        page.validation_warnings = BillValidator.validate_items(page)
        pages.append(page)

    warnings = BillValidator.detect_duplicates(pages)
    return BillExtractionResponse(
        is_success=True,
        token_usage=TokenUsage(**extractor.get_token_usage()),
        data=BillData(
            pagewise_line_items=pages,
            total_item_count=sum(len(page.bill_items) for page in pages),
            warnings=warnings,
        ),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.post("/extract-bill-data", response_model=BillExtractionResponse)
async def extract_bill_data(file: UploadFile = File(...)) -> BillExtractionResponse:
    try:
        content = await file.read(settings.max_file_size_bytes + 1)
        if len(content) > settings.max_file_size_bytes:
            raise DocumentSizeLimitError(
                f"Document exceeds the {settings.max_file_size_mb} MB upload limit"
            )
        return await run_in_threadpool(process_document, content)
    except DocumentSizeLimitError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except InvalidDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentConversionError as exc:
        logger.exception("Document conversion failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OCRServiceError as exc:
        logger.exception("OCR processing failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ExtractionConfigurationError as exc:
        logger.error("LLM extraction is not configured")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ExtractionError as exc:
        logger.exception("Structured extraction failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await file.close()
