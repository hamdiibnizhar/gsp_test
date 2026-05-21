from __future__ import annotations

import io


class OCRPDFReader:
    def __init__(
        self,
        *,
        ocr_enabled: bool = True,
        ocr_min_text_chars: int = 80,
        ocr_dpi: int = 200,
        ocr_lang: str = "eng",
    ) -> None:
        self.ocr_enabled = ocr_enabled
        self.ocr_min_text_chars = ocr_min_text_chars
        self.ocr_dpi = ocr_dpi
        self.ocr_lang = ocr_lang

    def read_bytes(self, data: bytes) -> str:
        text = self._extract_text(data)
        if not self._should_run_ocr(text):
            return text

        ocr_text = self._extract_text_with_ocr(data)
        combined = "\n\n".join(part.strip() for part in [text, ocr_text] if part.strip()).strip()
        if combined:
            return combined
        raise ValueError("PDF did not contain extractable text and OCR returned empty output")

    def _extract_text(self, data: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise ValueError("PDF support unavailable. Install `pypdf`.") from exc

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()

    def _extract_text_with_ocr(self, data: bytes) -> str:
        try:
            import pytesseract
            from pdf2image import convert_from_bytes
        except ImportError as exc:  # pragma: no cover
            raise ValueError(
                "OCR support unavailable. Install `pytesseract` and `pdf2image`."
            ) from exc

        pages = convert_from_bytes(data, dpi=self.ocr_dpi)
        parts = [
            pytesseract.image_to_string(page, lang=self.ocr_lang).strip()
            for page in pages
        ]
        return "\n".join(part for part in parts if part).strip()

    def _should_run_ocr(self, text: str) -> bool:
        return self.ocr_enabled and len(text.strip()) < self.ocr_min_text_chars
