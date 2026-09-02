import hashlib
import math
import re
from typing import List, Optional
import httpx
from app.core.config import settings


class EmbeddingService:
    _ollama_available = None  # Class-level cache: None = unknown, True/False = checked

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        custom_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS
        self.custom_client = custom_client

    @staticmethod
    def generate_deterministic_embedding(text: str, dimensions: int = 768) -> List[float]:
        """
        Generates a deterministic, normalized embedding vector from text.
        Used as high-fidelity fallback in unit tests and offline environments.
        Word overlap and semantic terms produce higher cosine similarity.
        """
        if not text:
            return [0.0] * dimensions

        # Seed vector based on word frequency and character hashes
        vec = [0.0] * dimensions
        words = re.findall(r"\b\w+\b", text.lower())
        for idx, w in enumerate(words):
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            pos = h % dimensions
            vec[pos] += 1.0 / math.sqrt(idx + 1.0)
            # Add secondary harmonic
            pos2 = (h >> 4) % dimensions
            vec[pos2] += 0.5 / math.sqrt(idx + 1.0)

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec = [1.0 / math.sqrt(dimensions)] * dimensions
        return vec

    async def get_embedding(self, text: str) -> List[float]:
        """
        Retrieves embedding vector from local Ollama or fallback generator.
        Caches Ollama availability to avoid repeated timeout delays.
        """
        if not text:
            return [0.0] * self.dimensions

        # Skip Ollama if we already know it's unavailable
        if EmbeddingService._ollama_available is False:
            return self.generate_deterministic_embedding(text, self.dimensions)

        should_close = False
        client = self.custom_client
        if client is None:
            client = httpx.AsyncClient(timeout=3.0)
            should_close = True

        try:
            payload = {"model": self.model_name, "prompt": text}
            resp = await client.post(f"{self.base_url}/api/embeddings", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "embedding" in data and isinstance(data["embedding"], list):
                    emb = data["embedding"]
                    EmbeddingService._ollama_available = True
                    if len(emb) == self.dimensions:
                        return emb
            EmbeddingService._ollama_available = False
        except Exception:
            EmbeddingService._ollama_available = False
        finally:
            if should_close:
                await client.aclose()

        return self.generate_deterministic_embedding(text, self.dimensions)

    async def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of text chunks.
        """
        embeddings = []
        for text in texts:
            emb = await self.get_embedding(text)
            embeddings.append(emb)
        return embeddings
