import re
from typing import Optional, Tuple


class SecurityGuardrailsEngine:
    PROMPT_INJECTION_PATTERNS = [
        (
            re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|commands)\b"),
            "Instruction override attempt",
        ),
        (
            re.compile(r"(?i)\b(system\s+prompt\s+override|system\s+prompt\s+leak|reveal\s+(your\s+)?(system\s+prompt|secret|keys|instructions))\b"),
            "System prompt extraction attempt",
        ),
        (
            re.compile(r"(?i)\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|jailbroken|unfiltered|unrestricted|god\s+mode)\b"),
            "Jailbreak roleplay attempt",
        ),
        (
            re.compile(r"(?i)\b(disregard|forget|bypass)\s+(all\s+)?(safety|ethical|system)\s+(guidelines|protocols|instructions|restrictions)\b"),
            "Safety bypass attempt",
        ),
        (
            re.compile(r"(?i)\b(output|print|display|dump|echo)\s+(the\s+)?(full|initial|internal|raw)\s+(prompt|instructions|system\s+message)\b"),
            "Prompt dumping attempt",
        ),
        (
            re.compile(r"(?i)\bpretend\s+you\s+have\s+no\s+(limits|rules|restrictions|filters|guidelines)\b"),
            "Filter evasion attempt",
        ),
    ]

    # Sensitive Data Redaction Regexes
    CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    API_KEY_REGEX = re.compile(r"\b(sk-[a-zA-Z0-9_-]{20,}|cs_[a-zA-Z0-9_-]{20,}|ck_[a-zA-Z0-9_-]{20,}|Bearer\s+[a-zA-Z0-9._-]{20,})\b")
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    PASSWORD_KEY_REGEX = re.compile(r"(?i)\b(password|passwd|secret_key|auth_token)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?")

    # Output XSS / Script Sanitization
    SCRIPT_TAG_REGEX = re.compile(r"(?i)<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>")
    JAVASCRIPT_URI_REGEX = re.compile(r"(?i)javascript:\s*")
    ON_EVENT_ATTR_REGEX = re.compile(r"(?i)\bon\w+\s*=\s*['\"][^'\"]*['\"]")

    @classmethod
    def detect_prompt_injection(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans input for known prompt injection, jailbreak, or system override attempts.
        """
        if not text:
            return False, None

        for pattern, reason in cls.PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return True, reason

        return False, None

    @classmethod
    def redact_sensitive_data(cls, text: str) -> str:
        """
        Masks credit cards, API keys, SSNs, and passwords from logs or LLM context.
        """
        if not text:
            return text

        # 1. Mask credit cards
        text = cls.CREDIT_CARD_REGEX.sub("[REDACTED_CARD_NUMBER]", text)

        # 2. Mask API keys
        text = cls.API_KEY_REGEX.sub("[REDACTED_API_KEY]", text)

        # 3. Mask SSNs
        text = cls.SSN_REGEX.sub("[REDACTED_SSN]", text)

        # 4. Mask password assignments
        text = cls.PASSWORD_KEY_REGEX.sub(r"\1: [REDACTED_SECRET]", text)

        return text

    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """
        Cleanses LLM output to prevent XSS payloads and script injections.
        """
        if not text:
            return text

        cleaned = cls.SCRIPT_TAG_REGEX.sub("", text)
        cleaned = cls.JAVASCRIPT_URI_REGEX.sub("", cleaned)
        cleaned = cls.ON_EVENT_ATTR_REGEX.sub("", cleaned)
        return cleaned

    @classmethod
    def process_and_inspect_input(cls, text: str) -> Tuple[str, bool, Optional[str]]:
        """
        Combined helper: redacts sensitive PII and tests for prompt injection.
        """
        redacted = cls.redact_sensitive_data(text)
        is_injection, reason = cls.detect_prompt_injection(text)
        return redacted, is_injection, reason
