from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from kafka import KafkaConsumer

from src.config import AppConfig
from src.rag import RAGService
from src.streaming.producer import KafkaIngestProducer
from src.streaming.schemas import IngestEvent


LOGGER = logging.getLogger("local_rag.streaming")


class KafkaIngestionConsumer:
    def __init__(self, config: AppConfig):
        self.config = config
        self.service = RAGService(config)
        self.producer = KafkaIngestProducer(config)
        self.consumer = KafkaConsumer(
            config.kafka_ingest_topic,
            config.kafka_retry_topic,
            bootstrap_servers=config.kafka_bootstrap_servers,
            group_id=config.kafka_group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        self.processed_dir = Path(config.processed_directory)
        self.failed_dir = Path(config.failed_directory)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def run_forever(self) -> None:
        for message in self.consumer:
            event = IngestEvent(**message.value)
            self.handle_event(event)

    def handle_event(self, event: IngestEvent) -> None:
        try:
            doc_name, raw_text = self.service.processor.read_path(event.file_path)
            self.service.ingest([(doc_name, raw_text)])
            self._move_file(event.file_path, self.processed_dir)
            LOGGER.info("Indexed %s", event.file_path)
        except Exception as exc:
            LOGGER.exception("Failed processing %s", event.file_path)
            self._handle_failure(event, exc)

    def _handle_failure(self, event: IngestEvent, exc: Exception) -> None:
        if event.retry_count + 1 < self.config.ingest_max_retries:
            retry_event = event.model_copy(
                update={"retry_count": event.retry_count + 1}
            )
            self.producer.publish(self.config.kafka_retry_topic, retry_event)
            return

        self.producer.publish(self.config.kafka_dlq_topic, event)
        self._move_file(event.file_path, self.failed_dir)
        LOGGER.error("Sent to DLQ: %s (%s)", event.file_path, exc)

    def _move_file(self, file_path: str, destination_dir: Path) -> None:
        source = Path(file_path)
        if not source.exists():
            return

        target = destination_dir / source.name
        if target.exists():
            target = destination_dir / f"{source.stem}-{source.stat().st_mtime_ns}{source.suffix}"
        shutil.move(str(source), str(target))


def main() -> None:
    consumer = KafkaIngestionConsumer(AppConfig.from_env())
    consumer.run_forever()


if __name__ == "__main__":
    main()
