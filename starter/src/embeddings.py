"""OpenRouter embeddings adapter using its OpenAI-compatible HTTP endpoint."""
from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .event_log import logged, record_event


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, question: str) -> list[float]: ...


class MyEmbedder:
    """Call a real embedding model; failures are surfaced without mock fallback."""

    endpoint = "https://openrouter.ai/api/v1/embeddings"
    dimensions = 1536

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.usage = []
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing from starter/.env")
        if not self.model_name:
            raise RuntimeError("EMBEDDING_MODEL is missing")

    @logged('embedding.request')
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model_name, "input": texts,
                              "dimensions": self.dimensions}).encode("utf-8")
        request = Request(
            self.endpoint,
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=90) as response:
                    result = json.loads(response.read().decode("utf-8"))
                rows = sorted(result["data"], key=lambda row: row["index"])
                self.usage.append(dict(model=result.get('model'), usage=result.get('usage', {}), id=result.get('id')))
                vectors = [row["embedding"] for row in rows]
                if len(vectors) != len(texts):
                    raise RuntimeError("Embedding response count did not match inputs")
                if any(len(vector) != self.dimensions for vector in vectors):
                    got = sorted({len(vector) for vector in vectors})
                    raise RuntimeError(f"Expected {self.dimensions} dimensions; got {got}")
                return vectors
            except HTTPError as exc:
                # A provider error body could echo confidential input. Log status only.
                record_event('embedding.request', 'http_error', level='error',
                             status=exc.code, attempt=attempt + 1, model=self.model_name)
                last_error = RuntimeError(f"OpenRouter returned HTTP {exc.code}")
                if exc.code < 500 and exc.code != 429:
                    break
            except (URLError, TimeoutError, KeyError, ValueError) as exc:
                record_event('embedding.request', 'attempt_failed', level='error',
                             error=exc, attempt=attempt + 1, model=self.model_name)
                last_error = RuntimeError(f"Embedding request failed: {type(exc).__name__}: {exc}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        assert last_error is not None
        raise last_error

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        # OpenRouter accepts an array of inputs. Batches keep requests bounded.
        for offset in range(0, len(texts), 64):
            vectors.extend(self._embed_batch(texts[offset:offset + 64]))
        return vectors

    def embed_query(self, question: str) -> list[float]:
        return self._embed_batch([question])[0]
