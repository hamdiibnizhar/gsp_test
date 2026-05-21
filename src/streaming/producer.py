from __future__ import annotations

import argparse
import json
from pathlib import Path

from kafka import KafkaProducer

from src.config import AppConfig
from src.streaming.schemas import IngestEvent


class KafkaIngestProducer:
    def __init__(self, config: AppConfig):
        self.config = config
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def publish(self, topic: str, event: IngestEvent) -> None:
        self.producer.send(topic, value=event.model_dump())
        self.producer.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path")
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()

    config = AppConfig.from_env()
    file_path = Path(args.file_path).resolve()
    event = IngestEvent(
        event_id=f"manual::{file_path.stat().st_mtime_ns}::{file_path.name}",
        file_path=str(file_path),
        file_name=file_path.name,
    )
    producer = KafkaIngestProducer(config)
    producer.publish(args.topic or config.kafka_ingest_topic, event)


if __name__ == "__main__":
    main()
