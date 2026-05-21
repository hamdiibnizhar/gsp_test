from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from fastapi import UploadFile

from src.document_processor.pdf_reader import OCRPDFReader


class DocumentProcessor:
    def __init__(
        self,
        chunk_size: int = 120,
        overlap: int = 30,
        *,
        ocr_enabled: bool = True,
        ocr_min_text_chars: int = 80,
        ocr_dpi: int = 200,
        ocr_lang: str = "eng",
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.pdf_reader = OCRPDFReader(
            ocr_enabled=ocr_enabled,
            ocr_min_text_chars=ocr_min_text_chars,
            ocr_dpi=ocr_dpi,
            ocr_lang=ocr_lang,
        )

    def read_path(self, path: str) -> Tuple[str, str]:
        file_path = Path(path)
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"File not found: {path}")
        return file_path.name, self._read_file(file_path)

    def read_upload(self, upload: UploadFile) -> Tuple[str, str]:
        payload = upload.file.read()
        if upload.filename is None:
            raise ValueError("Upload filename is required")
        suffix = Path(upload.filename).suffix.lower()
        if suffix in {".txt", ".md"}:
            return upload.filename, payload.decode("utf-8", errors="ignore")
        if suffix == ".pdf":
            return upload.filename, self.pdf_reader.read_bytes(payload)
        raise ValueError("Only .txt, .md, .pdf are supported")

    def clean(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def chunk(self, doc_name: str, text: str) -> List[Tuple[str, str]]:
        words = text.split()
        chunks: List[Tuple[str, str]] = []
        index = 0
        chunk_no = 1
        step = max(1, self.chunk_size - self.overlap)

        while index < len(words):
            chunk_text = " ".join(words[index : index + self.chunk_size])
            chunk_id = f"{Path(doc_name).stem}_{chunk_no:03d}"
            chunks.append((chunk_id, chunk_text))
            if index + self.chunk_size >= len(words):
                break
            index += step
            chunk_no += 1

        return chunks

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return self.pdf_reader.read_bytes(path.read_bytes())
        raise ValueError("Only .txt, .md, .pdf are supported")
