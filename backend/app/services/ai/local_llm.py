import re
from typing import Dict, List, Optional
import httpx
from app.core.config import settings


class LLMResponse:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int, model: str):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.model = model


class LocalLLMClient:
    _ollama_available = None  # Class-level cache

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        custom_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.custom_client = custom_client

    @staticmethod
    def _score_chunk_relevance(chunk: str, query: str) -> int:
        """Score how relevant a chunk is to the user query. Higher = more relevant."""
        chunk_lower = chunk.lower()
        query_words = [w for w in query.lower().split() if len(w) > 2]
        score = 0
        for word in query_words:
            if word in chunk_lower:
                score += 10
                # Bonus for exact word boundary match
                if re.search(r'\b' + re.escape(word) + r'\b', chunk_lower):
                    score += 5
        return score

    @staticmethod
    def _extract_product_answer(chunk: str, query: str) -> str:
        """Extract a clean, concise answer from a chunk based on the query."""
        # Remove common prefixes
        clean = chunk
        for prefix in [
            "Based on the official website information:",
            "Based on the official website information",
            "From the website:",
        ]:
            clean = clean.replace(prefix, "").strip()

        # Try to find product name (usually the first line or after a specific pattern)
        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        
        # Extract key sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip() and len(s.strip()) > 10]
        
        # Find sentences relevant to the query
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        relevant_sentences = []
        for s in sentences:
            s_lower = s.lower()
            if any(w in s_lower for w in query_words):
                relevant_sentences.append(s)

        # If we found relevant sentences, use them
        if relevant_sentences:
            answer = '. '.join(relevant_sentences[:3])
            if not answer.endswith('.'):
                answer += '.'
            return answer

        # Fallback: use first 2-3 meaningful sentences
        if sentences:
            answer = '. '.join(sentences[:3])
            if not answer.endswith('.'):
                answer += '.'
            return answer

        # Last resort: first 300 chars
        return clean[:300].strip() + ('...' if len(clean) > 300 else '')

    @staticmethod
    def _generate_deterministic_reply(system_prompt: str, user_prompt: str, context_chunks: Optional[List[str]] = None) -> str:
        """
        Deterministic, offline generation fallback for when Ollama is not running.
        Finds the most relevant chunk and extracts a clean answer.
        """
        if not context_chunks:
            return "I don't have that information. Would you like to connect with our support team?"

        # Score and sort chunks by relevance to query
        scored = [
            (LocalLLMClient._score_chunk_relevance(chunk, user_prompt), chunk)
            for chunk in context_chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        # Use the most relevant chunk
        best_chunk = scored[0][1]

        # Extract clean answer
        answer = LocalLLMClient._extract_product_answer(best_chunk, user_prompt)

        # Extract URL from the chunk
        urls = re.findall(r'https?://[^\s\)\n]+', best_chunk)
        if urls:
            answer += f"\n{urls[0]}"

        return answer

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        context_chunks: Optional[List[str]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """
        Generates a chat completion using local Ollama model (e.g. llama3.2).
        """
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for msg in chat_history[-6:]:  # Keep recent context window
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        should_close = False
        client = self.custom_client

        # Skip Ollama if we already know it's unavailable
        if LocalLLMClient._ollama_available is False:
            fallback_text = self._generate_deterministic_reply(system_prompt, user_prompt, context_chunks)
            return LLMResponse(
                content=fallback_text,
                prompt_tokens=len(user_prompt.split()) + 50,
                completion_tokens=len(fallback_text.split()),
                model=f"{self.model}-fallback",
            )

        if client is None:
            client = httpx.AsyncClient(timeout=5.0)
            should_close = True

        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                },
            }
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"].strip()
                    prompt_tokens = data.get("prompt_eval_count", len(user_prompt.split()))
                    comp_tokens = data.get("eval_count", len(content.split()))
                    LocalLLMClient._ollama_available = True
                    return LLMResponse(
                        content=content,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=comp_tokens,
                        model=self.model,
                    )
            LocalLLMClient._ollama_available = False
        except Exception:
            LocalLLMClient._ollama_available = False
        finally:
            if should_close:
                await client.aclose()

        fallback_text = self._generate_deterministic_reply(system_prompt, user_prompt, context_chunks)
        return LLMResponse(
            content=fallback_text,
            prompt_tokens=len(user_prompt.split()) + 50,
            completion_tokens=len(fallback_text.split()),
            model=f"{self.model}-fallback",
        )
