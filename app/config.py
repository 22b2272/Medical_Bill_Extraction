import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class Settings:
    max_file_size_mb: int
    max_pages: int
    default_dpi: int
    anthropic_api_key: str | None
    anthropic_model: str
    max_tokens: int

    @classmethod
    def from_environment(cls) -> "Settings":
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return cls(
            max_file_size_mb=_positive_int("MAX_FILE_SIZE_MB", 50),
            max_pages=_positive_int("MAX_DOCUMENT_PAGES", 50),
            default_dpi=_positive_int("PDF_RENDER_DPI", 300),
            anthropic_api_key=api_key or None,
            anthropic_model=os.getenv(
                "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"
            ).strip(),
            max_tokens=_positive_int("ANTHROPIC_MAX_TOKENS", 4096),
        )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings.from_environment()
