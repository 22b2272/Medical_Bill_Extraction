import cv2
import numpy as np

from .document_io import InvalidDocumentError


class DocumentPreprocessor:
    """Image enhancement used before OCR."""

    @staticmethod
    def enhance_image(image_bytes: bytes) -> bytes:
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidDocumentError("The page image could not be decoded")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray)
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        foreground = np.column_stack(np.where(binary < 255))
        if foreground.size:
            angle = cv2.minAreaRect(foreground)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if 0.5 < abs(angle) < 45:
                height, width = binary.shape
                center = (width // 2, height // 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                binary = cv2.warpAffine(
                    binary,
                    matrix,
                    (width, height),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

        encoded, buffer = cv2.imencode(".png", binary)
        if not encoded:
            raise RuntimeError("Unable to encode the preprocessed page")
        return buffer.tobytes()

    @staticmethod
    def experimental_visual_flags(image_bytes: bytes) -> list[str]:
        """Return unvalidated visual heuristics; these are not fraud determinations."""
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidDocumentError("The page image could not be decoded")

        flags: list[str] = []
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        white_mask = cv2.inRange(hsv, (0, 0, 200), (180, 30, 255))
        white_ratio = float(np.count_nonzero(white_mask)) / white_mask.size
        if white_ratio > 0.15:
            flags.append("High proportion of near-white pixels (unvalidated heuristic)")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if len(contours) > 1000:
            flags.append("High edge-contour count (unvalidated heuristic)")
        return flags
