import enum
import re
from typing import Any, Dict, Optional


class ToolType(str, enum.Enum):
    KNOWLEDGE_INQUIRY = "knowledge_inquiry"
    SEARCH_PRODUCT = "search_product"
    GET_PRODUCT = "get_product"
    ADD_TO_CART = "add_to_cart"
    ESCALATE_HUMAN = "escalate_to_human"


class ToolCallResult:
    def __init__(self, tool: ToolType, parameters: Dict[str, Any], confidence: float = 1.0):
        self.tool = tool
        self.parameters = parameters
        self.confidence = confidence

    def to_dict(self):
        return {
            "tool": self.tool.value,
            "parameters": self.parameters,
            "confidence": round(self.confidence, 2),
        }


class ToolSelectionEngine:
    HUMAN_KEYWORDS = [
        "human", "agent", "person", "representative", "whatsapp",
        "speak to someone", "talk to support", "escalate", "real person",
        "customer service phone", "live agent"
    ]

    ADD_TO_CART_PATTERNS = [
        r"add\s+(?:this|to\s+cart|to\s+bag|item)",
        r"buy\s+now",
        r"purchase\s+this",
        r"order\s+(?:this|item)",
    ]

    # "What is X" or "tell me about X" patterns -> knowledge inquiry
    KNOWLEDGE_PATTERNS = [
        r"^what\s+(?:is|are|does|do)",
        r"^tell\s+me\s+about",
        r"^how\s+(?:do|does|is|are|can|could)",
        r"^why\s+(?:is|are|do|does|can|could)",
        r"^when\s+(?:is|are|do|does|can|could)",
        r"^where\s+(?:is|are|do|does|can|could)",
        r"^can\s+(?:you|i|we)",
        r"^do\s+you\s+(?:have|offer|provide|sell|carry)",
        r"^what's\s+the\s+(?:difference|policy|process|procedure)",
    ]

    # Product purchase/search intent keywords
    BUY_INTENT_KEYWORDS = [
        "buy", "purchase", "shop", "add to cart", "order",
        "price", "cost", "how much", "discount", "sale",
        "in stock", "available", "stock",
    ]

    PRODUCT_KEYWORDS = [
        "product", "products", "item", "items", "catalog",
        "shoes", "keyboard", "headphones", "clothing",
        "grenade", "smoke", "bomb", "firework", "fireworks", "cannon",
        "paintball", "airsoft",
        "bundle", "pack", "kit", "set",
    ]

    POLICY_AND_FAQ_KEYWORDS = [
        "shipping", "delivery", "return", "refund", "policy", "policies",
        "warranty", "guarantee", "hours", "contact", "address", "terms",
        "faq", "track my order", "order status", "location", "store hours",
    ]

    @classmethod
    def classify(cls, user_message: str) -> ToolCallResult:
        msg_lower = user_message.strip().lower()

        # 1. Check Human Escalation / WhatsApp
        for kw in cls.HUMAN_KEYWORDS:
            if kw in msg_lower:
                return ToolCallResult(
                    tool=ToolType.ESCALATE_HUMAN,
                    parameters={"reason": "Customer explicitly requested human support"},
                    confidence=0.95,
                )

        # 2. Check Add to Cart
        for pat in cls.ADD_TO_CART_PATTERNS:
            if re.search(pat, msg_lower):
                return ToolCallResult(
                    tool=ToolType.ADD_TO_CART,
                    parameters={"query": user_message},
                    confidence=0.90,
                )

        # 3. Check Policy / FAQ
        for kw in cls.POLICY_AND_FAQ_KEYWORDS:
            if kw in msg_lower:
                return ToolCallResult(
                    tool=ToolType.KNOWLEDGE_INQUIRY,
                    parameters={"query": user_message},
                    confidence=0.95,
                )

        # 4. Check "What is X" / informational patterns -> knowledge inquiry first
        for pat in cls.KNOWLEDGE_PATTERNS:
            if re.search(pat, msg_lower):
                return ToolCallResult(
                    tool=ToolType.KNOWLEDGE_INQUIRY,
                    parameters={"query": user_message},
                    confidence=0.90,
                )

        # 5. Check Buy Intent + Product keywords -> product search
        has_buy_intent = any(kw in msg_lower for kw in cls.BUY_INTENT_KEYWORDS)
        has_product_keyword = any(kw in msg_lower for kw in cls.PRODUCT_KEYWORDS)

        if has_buy_intent and has_product_keyword:
            return ToolCallResult(
                tool=ToolType.SEARCH_PRODUCT,
                parameters={"query": user_message},
                confidence=0.90,
            )

        # 6. Standalone product keywords (no "what is" prefix) -> product search
        if has_product_keyword:
            return ToolCallResult(
                tool=ToolType.SEARCH_PRODUCT,
                parameters={"query": user_message},
                confidence=0.80,
            )

        # 7. Default: Knowledge Inquiry via RAG
        return ToolCallResult(
            tool=ToolType.KNOWLEDGE_INQUIRY,
            parameters={"query": user_message},
            confidence=0.90,
        )
