from __future__ import annotations

import logging
from typing import Optional

import httpx


LOGGER = logging.getLogger("local_rag.ollama")


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_answer(self, question: str, context: str) -> Optional[str]:
        prompt = (
            "Jawab pertanyaan hanya berdasarkan konteks yang diberikan. "
            "Jika konteks tidak cukup, katakan bahwa jawaban tidak ditemukan.\n\n"
            f"Pertanyaan: {question}\n\n"
            f"Konteks:\n{context}\n"
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
            data = response.json()
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Ollama request failed: %s", exc)
            return None

        answer = data.get("response")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
        return None
