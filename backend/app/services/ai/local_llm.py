import json
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
    def _generate_deterministic_reply(system_prompt: str, user_prompt: str, context_chunks: Optional[List[str]] = None) -> str:
        """
        Deterministic, offline generation fallback for test environments and when Ollama is not running.
        Strictly grounds the answer on provided RAG context chunks.
        """
        if context_chunks and len(context_chunks) > 0:
            primary_chunk = context_chunks[0]
            # Formulate clean, natural grounded answer
            first_sentence = primary_chunk.split(".")[0].strip()
            return f"Based on the official website information: {primary_chunk}\n\nIs there anything else I can help you with regarding this?"
        
        return "I apologize, but I do not have verified website information to answer that question accurately. Would you like to connect directly with our customer support team?"

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
