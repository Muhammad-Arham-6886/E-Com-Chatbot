import json
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.website import Website
from app.services.ai.commerce_provider import CommerceProvider, MockCommerceProvider, ProductCard
from app.services.ai.local_llm import LocalLLMClient
from app.services.ai.tool_selector import ToolSelectionEngine, ToolType, ToolCallResult
from app.services.rag.vector_search import VectorSearchService


class SourceCitation:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url

    def to_dict(self):
        return {"title": self.title, "url": self.url}


class SuggestedAction:
    def __init__(self, action_type: str, label: str, value: str, payload: Optional[Dict[str, Any]] = None):
        self.action_type = action_type
        self.label = label
        self.value = value
        self.payload = payload or {}

    def to_dict(self):
        return {
            "type": self.action_type,
            "label": self.label,
            "value": self.value,
            "payload": self.payload,
        }


class RAGResponse:
    def __init__(
        self,
        content: str,
        sources: List[SourceCitation],
        suggested_actions: List[SuggestedAction],
        tool_call: ToolCallResult,
        token_count: int,
    ):
        self.content = content
        self.sources = sources
        self.suggested_actions = suggested_actions
        self.tool_call = tool_call
        self.token_count = token_count


class RAGEngine:
    def __init__(
        self,
        db: AsyncSession,
        llm_client: Optional[LocalLLMClient] = None,
        commerce_provider: Optional[CommerceProvider] = None,
    ):
        self.db = db
        self.llm_client = llm_client or LocalLLMClient()
        self.commerce_provider = commerce_provider
        self.vector_search = VectorSearchService(db)

    def _build_grounded_system_prompt(self, website: Website, context_chunks: List[str]) -> str:
        base_instructions = (
            f"You are the AI customer support for '{website.name}' ({website.domain}).\n\n"
            "RULES:\n"
            "- Answer in 1-3 sentences. Be direct and specific.\n"
            "- Use ONLY the context below. Never make up information.\n"
            "- If the context mentions a product, include the product name and price if available.\n"
            "- If context has a URL, include it.\n"
            "- If you don't have the answer, say 'I don't have that info' and offer to connect with support.\n"
            "- No greetings, no filler, no stories. Just the answer.\n"
            "- Never say 'Based on the official website information' or similar prefixes.\n"
            "- Never end with 'Is there anything else I can help you with?'"
        )

        if website.settings and website.settings.custom_instructions:
            base_instructions += f"\n\nStore Specific Guidelines:\n{website.settings.custom_instructions}"

        context_str = "\n\n---\n\n".join(context_chunks) if context_chunks else "No website context available."
        return f"{base_instructions}\n\n=== VERIFIED WEBSITE CONTEXT ===\n{context_str}\n================================"

    async def process_query(
        self,
        user_message: str,
        website: Website,
        chat_history: Optional[List[ChatMessage]] = None,
    ) -> RAGResponse:
        # 1. Tool / Intent Classification
        tool_result = ToolSelectionEngine.classify(user_message)
        sources: List[SourceCitation] = []
        actions: List[SuggestedAction] = []

        # Check WhatsApp escalation setting
        whatsapp_action = None
        from app.services.whatsapp_service import WhatsAppHandoffService
        wa_payload = WhatsAppHandoffService.generate_handoff_payload(
            website=website,
            session_id=chat_history[0].session_id if chat_history else "",
            visitor_id="Visitor",
            last_user_message=user_message,
        )
        if wa_payload["is_enabled"] and wa_payload["handoff_url"]:
            whatsapp_action = SuggestedAction(
                action_type="whatsapp_handoff",
                label="Chat on WhatsApp",
                value=wa_payload["handoff_url"],
                payload={"prefilled_message": wa_payload["prefilled_message"]},
            )

        # 2. Handle Human Escalation Intent
        if tool_result.tool == ToolType.ESCALATE_HUMAN:
            if whatsapp_action:
                actions.append(whatsapp_action)
                reply = "Connecting you to our support team on WhatsApp."
            else:
                reply = "I'll connect you with our support team. Please leave your details and we'll get back to you."

            return RAGResponse(
                content=reply,
                sources=[],
                suggested_actions=actions,
                tool_call=tool_result,
                token_count=len(reply.split()),
            )

        # 3. Handle Product Search or Add to Cart via Commerce Provider
        if tool_result.tool in (ToolType.SEARCH_PRODUCT, ToolType.ADD_TO_CART, ToolType.GET_PRODUCT):
            from app.services.ai.commerce_provider import get_commerce_provider_for_website
            provider = self.commerce_provider or await get_commerce_provider_for_website(self.db, website.id)
            products = await provider.search_products(user_message, limit=3)
            for prod in products:
                actions.append(
                    SuggestedAction(
                        action_type="product_card",
                        label=prod.name,
                        value=prod.product_url,
                        payload=prod.to_dict(),
                    )
                )

            if products:
                reply = ""
                for p in products:
                    reply += f"{p.name} - ${p.price:.2f}\n"
                    if p.description:
                        # Truncate description to 1-2 sentences
                        short_desc = '. '.join(p.description.split('.')[:2]).strip()
                        if not short_desc.endswith('.'):
                            short_desc += '.'
                        reply += f"{short_desc}\n"
                    reply += f"Link: {p.product_url}\n\n"
                reply = reply.strip()
            else:
                reply = "I searched our product catalog but couldn't find exact matches for that item. Would you like me to connect you with a representative?"
                if whatsapp_action:
                    actions.append(whatsapp_action)

            return RAGResponse(
                content=reply,
                sources=[],
                suggested_actions=actions,
                tool_call=tool_result,
                token_count=len(reply.split()),
            )

        # 4. Handle Knowledge Inquiry (RAG)
        search_hits = await self.vector_search.search(
            query=user_message,
            org_id=website.organization_id,
            website_id=website.id,
            top_k=4,
            min_similarity=0.05,
        )

        context_chunks: List[str] = []
        seen_urls = set()
        for hit in search_hits:
            context_chunks.append(hit.content)
            if hit.url not in seen_urls:
                seen_urls.add(hit.url)
                sources.append(SourceCitation(title=hit.title, url=hit.url))

        # Format history for LLM client
        history_formatted = []
        if chat_history:
            for msg in chat_history:
                role = "assistant" if msg.sender == "BOT" else "user"
                history_formatted.append({"role": role, "content": msg.content})

        system_prompt = self._build_grounded_system_prompt(website, context_chunks)

        llm_resp = await self.llm_client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_message,
            chat_history=history_formatted,
            context_chunks=context_chunks,
        )

        # If LLM indicates lack of knowledge and WhatsApp is enabled, suggest WhatsApp
        if "don't have" in llm_resp.content.lower() or "do not have" in llm_resp.content.lower():
            if whatsapp_action:
                actions.append(whatsapp_action)

        return RAGResponse(
            content=llm_resp.content,
            sources=sources,
            suggested_actions=actions,
            tool_call=tool_result,
            token_count=llm_resp.prompt_tokens + llm_resp.completion_tokens,
        )
