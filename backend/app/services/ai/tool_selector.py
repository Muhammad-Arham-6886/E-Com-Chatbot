import enum
import re
from typing import Any, Dict, Optional


class ToolType(str, enum.Enum):
    KNOWLEDGE_INQUIRY = "knowledge_inquiry"
    SEARCH_PRODUCT = "search_product"
    GET_PRODUCT = "get_product"
    ADD_TO_CART = "add_to_cart"
    ESCALATE_HUMAN = "escalate_to_human"
    GREETING = "greeting"


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
        r"^what's\s+the\s+(?:difference|policy|process|procedure)",
    ]

    # "Do you sell X", "Do you have X" -> try product search first
    PRODUCT_AVAILABILITY_PATTERNS = [
        r"^do\s+you\s+(?:have|sell|offer|provide|carry|stock|supply)",
        r"^can\s+you\s+(?:get|order|find|source)",
        r"^is\s+there\s+a\s+",
        r"^are\s+you\s+(?:selling|stocking)",
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
        "doll", "dolls", "baby", "reborn", "teddy", "toy", "toys", "pushchair",
        "blanket", "cushion", "pram", "cot", "carrier",
        "bundle", "pack", "kit", "set",
    ]

    # Question starters -> user is asking a question, not searching by name
    QUESTION_PATTERNS = [
        r"^what\b", r"^who\b", r"^when\b", r"^where\b", r"^why\b", r"^how\b",
        r"^is\b", r"^are\b", r"^do\b", r"^does\b", r"^can\b", r"^could\b",
        r"^would\b", r"^will\b", r"^should\b", r"^have\b", r"^has\b",
        r"^tell\s+me\b", r"^show\s+me\b", r"^give\s+me\b",
        r"\?$",
    ]

    @classmethod
    def _looks_like_question(cls, msg_lower: str) -> bool:
        return any(re.match(p, msg_lower) for p in cls.QUESTION_PATTERNS)

    POLICY_AND_FAQ_KEYWORDS = [
        "shipping", "delivery", "return", "refund", "policy", "policies",
        "warranty", "guarantee", "hours", "contact", "address", "terms",
        "faq", "track my order", "order status", "location", "store hours",
    ]

    GREETING_KEYWORDS = [
        "hi", "hello", "hey", "good morning", "good afternoon",
        "good evening", "how are you", "whats up", "what's up",
    ]

    @classmethod
    def classify(cls, user_message: str) -> ToolCallResult:
        msg_lower = user_message.strip().lower()

        # 0. Check Greeting (very short messages only)
        short_msg = len(user_message.strip()) < 40
        if short_msg and any(g in msg_lower for g in cls.GREETING_KEYWORDS):
            return ToolCallResult(
                tool=ToolType.GREETING,
                parameters={"query": user_message},
                confidence=0.90,
            )

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

        # 3.5 Check product availability ("Do you sell X", "Do you have X") -> product search
        for pat in cls.PRODUCT_AVAILABILITY_PATTERNS:
            if re.search(pat, msg_lower):
                return ToolCallResult(
                    tool=ToolType.SEARCH_PRODUCT,
                    parameters={"query": user_message},
                    confidence=0.85,
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

        # 6.5 Not a question and no policy/pattern match -> likely a product name search
        if not cls._looks_like_question(msg_lower):
            return ToolCallResult(
                tool=ToolType.SEARCH_PRODUCT,
                parameters={"query": user_message},
                confidence=0.70,
            )

        # 7. Default: Knowledge Inquiry via RAG
        return ToolCallResult(
            tool=ToolType.KNOWLEDGE_INQUIRY,
            parameters={"query": user_message},
            confidence=0.90,
        )
