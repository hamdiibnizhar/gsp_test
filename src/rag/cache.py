from __future__ import annotations

import json
import logging
from typing import Optional


LOGGER = logging.getLogger("local_rag")


class LocalResponseCache:
    def __init__(self) -> None:
        self._entries: dict[str, dict] = {}

    def get(self, cache_key: str) -> Optional[dict]:
        return self._entries.get(cache_key)

    def set(self, cache_key: str, value: dict) -> None:
        self._entries[cache_key] = value

    def clear(self) -> None:
        self._entries.clear()


class RedisResponseCache:
    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str,
        ttl_seconds: int = 0,
        enabled: bool = True,
    ) -> None:
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        self.fallback = LocalResponseCache()
        self.client = None

        if not enabled:
            return

        try:
            import redis

            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Redis unavailable, falling back to local cache: %s", exc)
            self.client = None

    def get(self, cache_key: str) -> Optional[dict]:
        if self.client is None:
            return self.fallback.get(cache_key)

        payload = self.client.get(self._materialize_key(cache_key))
        if payload is None:
            return None
        return json.loads(payload)

    def set(self, cache_key: str, value: dict) -> None:
        if self.client is None:
            self.fallback.set(cache_key, value)
            return

        materialized_key = self._materialize_key(cache_key)
        payload = json.dumps(value)
        if self.ttl_seconds > 0:
            self.client.set(materialized_key, payload, ex=self.ttl_seconds)
        else:
            self.client.set(materialized_key, payload)

    def clear(self) -> None:
        if self.client is None:
            self.fallback.clear()
            return
        self.client.incr(self._version_key)

    @property
    def _version_key(self) -> str:
        return f"{self.key_prefix}:version"

    def _materialize_key(self, cache_key: str) -> str:
        if self.client is None:
            return cache_key

        version = self.client.get(self._version_key)
        if version is None:
            version = "1"
            self.client.set(self._version_key, version)
        return f"{self.key_prefix}:v{version}:{cache_key}"
