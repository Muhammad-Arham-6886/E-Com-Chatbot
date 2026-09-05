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

    # Words to ignore when scoring relevance
    STOP_WORDS = {
        "i", "me", "my", "we", "our", "you", "your", "it", "its",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "do", "does", "did", "have", "has", "had", "can", "could",
        "will", "would", "should", "may", "might", "shall",
        "this", "that", "these", "those", "what", "which", "who",
        "how", "when", "where", "why", "if", "or", "and", "but",
        "not", "no", "so", "very", "too", "also", "just",
        "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "about", "like", "as", "than", "then", "now", "here", "there",
        "tell", "want", "need", "get", "know", "please",
    }

    @classmethod
    def _get_query_keywords(cls, query: str) -> List[str]:
        """Extract meaningful keywords from a query, sorted by importance."""
        words = query.lower().split()
        # Keep words that are > 2 chars and not stop words
        keywords = [w for w in words if len(w) > 2 and w not in cls.STOP_WORDS]
        return keywords

    @classmethod
    def _score_chunk_relevance(cls, chunk: str, query: str) -> float:
        """
        Score how relevant a chunk is to the user query.
        Returns 0.0 to 1.0. Higher = more relevant.
        A chunk MUST contain at least one key query word to score > 0.
        """
        chunk_lower = chunk.lower()
        keywords = cls._get_query_keywords(query)

        if not keywords:
            return 0.0

        matched = 0
        total_occurrences = 0
        for word in keywords:
            count = chunk_lower.count(word)
            if count > 0:
                matched += 1
                total_occurrences += count

        if matched == 0:
            return 0.0

        # Base score = percentage of query keywords found in chunk
        base_score = matched / len(keywords)

        # Keyword density bonus: chunks mentioning keywords multiple times are more relevant
        density_boost = min(0.2, total_occurrences * 0.05)

        # Phrase bonus: adjacent meaningful words from the query appearing in order
        phrase_boost = 0.0
        words = query.lower().split()
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if len(w1) > 2 and len(w2) > 2 and w1 not in cls.STOP_WORDS and w2 not in cls.STOP_WORDS:
                if f"{w1} {w2}" in chunk_lower:
                    phrase_boost += 0.15
        phrase_boost = min(0.15, phrase_boost)

        # Complete keyword match ALWAYS beats partial matches
        if matched == len(keywords):
            return min(2.0, 1.0 + 0.4 + density_boost + phrase_boost)

        # Partial matches stay below 1.0
        return min(0.99, base_score + min(0.3, density_boost + phrase_boost))

    @staticmethod
    def _is_do_you_have_query(query: str) -> bool:
        """Check if the query is asking 'do you have X' or similar."""
        patterns = [
            r"do\s+you\s+have",
            r"do\s+you\s+sell",
            r"do\s+you\s+carry",
            r"do\s+you\s+stock",
            r"can\s+you\s+get",
            r"are\s+you\s+selling",
            r"is\s+there\s+a",
            r"where\s+(?:can|i)\s+(?:find|get|buy)",
        ]
        q = query.lower().strip()
        return any(re.search(p, q) for p in patterns)

    @staticmethod
    def _extract_answer(chunk: str, query: str) -> str:
        """Extract a clean, concise answer from the best matching chunk."""
        # Remove common prefixes
        clean = chunk
        for prefix in [
            "Based on the official website information:",
            "Based on the official website information",
            "From the website:",
            "Website says:",
        ]:
            clean = clean.replace(prefix, "").strip()

        # Split into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip() and len(s.strip()) > 5]

        # Get query keywords
        keywords = [w.lower() for w in query.split() if len(w) > 2 and w not in LocalLLMClient.STOP_WORDS]

        # Score each sentence by keyword match count
        scored_sentences = []
        for s in sentences:
            s_lower = s.lower()
            match_count = sum(1 for w in keywords if w in s_lower)
            scored_sentences.append((match_count, s))

        # Sort by match count descending
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        # Take top sentences that have at least 1 keyword match
        relevant = [s for count, s in scored_sentences if count > 0][:3]

        # If no sentence matches any keyword, take first 2 sentences as fallback
        use_sentences = relevant if relevant else sentences[:2]

        if not use_sentences:
            return "I don't have that information."

        answer = '. '.join(use_sentences)
        if not answer.endswith('.'):
            answer += '.'

        # Extract and append URL if present
        urls = re.findall(r'https?://[^\s\)\n]+', chunk)
        if urls:
            answer += f"\n{urls[0]}"

        return answer

    @classmethod
    def _generate_deterministic_reply(cls, system_prompt: str, user_prompt: str, context_chunks: Optional[List[str]] = None) -> str:
        """
        Deterministic, offline generation fallback for when Ollama is not running.
        Finds the MOST relevant chunk and extracts a clean answer.
        Returns 'I don't have that info' if no chunk is relevant enough.
        """
        if not context_chunks:
            return "I don't have that information. Would you like to connect with our support team?"

        # Score all chunks
        scored = [
            (cls._score_chunk_relevance(chunk, user_prompt), chunk)
            for chunk in context_chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_chunk = scored[0]

        # If best chunk has 0 relevance, we don't have the answer
        if best_score < 0.15:
            if cls._is_do_you_have_query(user_prompt):
                return "We don't currently carry that product. Would you like me to connect you with our team?"
            return "I don't have that information. Would you like to connect with our support team?"

        # Extract clean answer from best chunk
        answer = cls._extract_answer(best_chunk, user_prompt)

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
            for msg in chat_history[-6:]:
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
