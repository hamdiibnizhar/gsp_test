from __future__ import annotations

import hashlib
import time
from pathlib import Path

from src.config import AppConfig
from src.streaming.producer import KafkaIngestProducer
from src.streaming.schemas import IngestEvent


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


class DirectoryWatcher:
    def __init__(self, config: AppConfig):
        self.config = config
        self.watch_dir = Path(config.watch_directory)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.pending: dict[str, tuple[int, float]] = {}
        self.published: set[str] = set()
        self.producer = KafkaIngestProducer(config)

    def run_forever(self) -> None:
        while True:
            self.scan_once()
            time.sleep(self.config.watcher_poll_seconds)

    def scan_once(self) -> None:
        now = time.time()
        for file_path in sorted(self.watch_dir.iterdir()):
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            stat = file_path.stat()
            signature = self._signature(file_path, stat.st_size, stat.st_mtime_ns)
            if signature in self.published:
                continue

            current = self.pending.get(str(file_path))
            if current is None or current[0] != stat.st_size:
                self.pending[str(file_path)] = (stat.st_size, now)
                continue

            stable_since = current[1]
            if now - stable_since < self.config.watcher_stable_seconds:
                continue

            event = IngestEvent(
                event_id=signature,
                file_path=str(file_path.resolve()),
                file_name=file_path.name,
            )
            self.producer.publish(self.config.kafka_ingest_topic, event)
            self.published.add(signature)
            self.pending.pop(str(file_path), None)

    def _signature(self, file_path: Path, size: int, mtime_ns: int) -> str:
        raw = f"{file_path.resolve()}::{size}::{mtime_ns}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> None:
    watcher = DirectoryWatcher(AppConfig.from_env())
    watcher.run_forever()


if __name__ == "__main__":
    main()
