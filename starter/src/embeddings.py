import os
import time
from typing import Protocol
import requests


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


class LocalMiniLMEmbedder:
    """Fast local embedding model running all-MiniLM-L6-v2 via ONNX (no API key needed)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=self.model_name)
        # Determine dimensions
        sample = list(self._model.embed(["init test"]))[0]
        self.dimensions = len(sample)

    def embed_documents(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Embed document chunks locally in batches."""
        results: list[list[float]] = []
        # fastembed generators yield numpy arrays
        for emb in self._model.embed(texts, batch_size=batch_size):
            results.append(emb.tolist())
        return results

    def embed_query(self, question: str) -> list[float]:
        """Embed a single query locally."""
        generator = self._model.embed([question])
        vec = next(iter(generator))
        return vec.tolist()


class GeminiEmbedder:
    """Embedding adapter using Google Gemini API (gemini-embedding-001)."""

    def __init__(
        self,
        model_name: str = "models/gemini-embedding-001",
        api_key: str | None = None,
        dimensions: int = 768,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.dimensions = dimensions

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY chưa được thiết lập trong môi trường hoặc .env")

        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        sample_vec = self.embed_query("init test")
        if len(sample_vec) != self.dimensions:
            self.dimensions = len(sample_vec)

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        results: list[list[float]] = []
        batch_url = f"{self.base_url}/{self.model_name}:batchEmbedContents?key={self.api_key}"

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            requests_payload = []
            for t in batch:
                requests_payload.append(
                    {
                        "model": self.model_name,
                        "content": {"parts": [{"text": t}]},
                        "outputDimensionality": self.dimensions,
                    }
                )

            payload = {"requests": requests_payload}

            for attempt in range(5):
                resp = requests.post(batch_url, json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json().get("embeddings", [])
                    results.extend([item["values"] for item in data])
                    break
                elif resp.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                else:
                    raise RuntimeError(f"Gemini batch embedding failed [{resp.status_code}]: {resp.text}")
            else:
                raise RuntimeError(f"Gemini batch embedding failed after retries: {resp.text}")

            time.sleep(0.2)

        return results

    def embed_query(self, question: str) -> list[float]:
        url = f"{self.base_url}/{self.model_name}:embedContent?key={self.api_key}"
        payload = {
            "model": self.model_name,
            "content": {"parts": [{"text": question}]},
            "outputDimensionality": self.dimensions,
        }

        for attempt in range(5):
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["embedding"]["values"]
            elif resp.status_code == 429:
                time.sleep(2 * (attempt + 1))
            else:
                raise RuntimeError(f"Gemini embedding failed [{resp.status_code}]: {resp.text}")

        raise RuntimeError("Gemini embedding failed after retries")


class DeployComEmbedder:
    """Adapter gọi endpoint /v1/embeddings từ deploy.com (OpenAI-compatible)."""

    def __init__(self, model_name: str | None = None, base_url: str | None = None, api_key: str | None = None) -> None:
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.base_url = (base_url or os.getenv("DEPLOY_BASE_URL", "https://api-sf1-cdn.deploy.com/api/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("DEPLOY_API_KEY", "")

        if not self.api_key:
            raise ValueError("DEPLOY_API_KEY chưa được thiết lập trong môi trường hoặc .env")

        self.endpoint = f"{self.base_url}/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        sample_vec = self.embed_query("init test")
        self.dimensions = len(sample_vec)

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": self.model_name,
                "input": batch,
            }
            resp = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f"Embedding request failed [{resp.status_code}]: {resp.text}")

            data = resp.json()["data"]
            data.sort(key=lambda x: x["index"])
            results.extend([item["embedding"] for item in data])

        return results

    def embed_query(self, question: str) -> list[float]:
        payload = {
            "model": self.model_name,
            "input": [question],
        }
        resp = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding request failed [{resp.status_code}]: {resp.text}")

        return resp.json()["data"][0]["embedding"]
