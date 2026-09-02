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

    PRODUCT_SEARCH_KEYWORDS = [
        "product", "products", "item", "items", "catalog", "buy", "shop",
        "price of", "how much is", "do you sell", "looking for", "recommend",
        "discount", "inventory", "stock", "shoes", "keyboard", "headphones",
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

        # 3. Check Policy / FAQ Knowledge Inquiry priority (e.g. "How much is shipping?")
        for kw in cls.POLICY_AND_FAQ_KEYWORDS:
            if kw in msg_lower:
                return ToolCallResult(
                    tool=ToolType.KNOWLEDGE_INQUIRY,
                    parameters={"query": user_message},
                    confidence=0.95,
                )

        # 4. Check Product Search / Commerce Inquiry
        for kw in cls.PRODUCT_SEARCH_KEYWORDS:
            if kw in msg_lower:
                return ToolCallResult(
                    tool=ToolType.SEARCH_PRODUCT,
                    parameters={"query": user_message},
                    confidence=0.85,
                )

        # 5. Default: Knowledge Inquiry via RAG
        return ToolCallResult(
            tool=ToolType.KNOWLEDGE_INQUIRY,
            parameters={"query": user_message},
            confidence=0.90,
        )
