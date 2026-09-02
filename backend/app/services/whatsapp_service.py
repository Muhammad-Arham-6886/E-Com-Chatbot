import re
import urllib.parse
from typing import Optional
from app.models.website import Website


class WhatsAppHandoffService:
    DEFAULT_TEMPLATE = (
        "Hello {store_name}, I was chatting with your AI assistant (Visitor: {visitor_id}) "
        "regarding: \"{last_inquiry}\". Could a human support agent please assist me?"
    )

    @staticmethod
    def normalize_phone_number(raw_number: Optional[str]) -> str:
        """
        Normalizes international phone numbers by stripping formatting characters,
        plus signs, spaces, hyphens, and leading double-zeros (00).
        """
        if not raw_number:
            return ""
        # Remove any character that is not a digit
        digits = re.sub(r"\D", "", raw_number.strip())
        # Strip leading '00' international prefix if present
        if digits.startswith("00"):
            digits = digits[2:]
        return digits

    @classmethod
    def format_message_template(
        cls,
        template: Optional[str],
        store_name: str,
        visitor_id: str,
        session_id: str,
        last_inquiry: str,
    ) -> str:
        """
        Interpolates customizable template variables:
        {store_name}, {visitor_id}, {session_id}, {last_inquiry}
        """
        tmpl = template.strip() if (template and template.strip()) else cls.DEFAULT_TEMPLATE
        
        # Clean inquiry text if too long (cap at 180 chars for clean readability in WhatsApp preview)
        clean_inquiry = last_inquiry.strip() if last_inquiry else "General product inquiry"
        if len(clean_inquiry) > 180:
            clean_inquiry = clean_inquiry[:177] + "..."

        formatted = (
            tmpl.replace("{store_name}", store_name)
            .replace("{website_name}", store_name)
            .replace("{visitor_id}", visitor_id)
            .replace("{session_id}", session_id[:8] if session_id else "")
            .replace("{last_inquiry}", clean_inquiry)
        )
        return formatted

    @classmethod
    def build_handoff_url(
        cls,
        raw_phone: str,
        message_text: str,
    ) -> str:
        """
        Constructs the official click-to-chat WhatsApp deep link.
        """
        clean_phone = cls.normalize_phone_number(raw_phone)
        if not clean_phone:
            return ""
        encoded_text = urllib.parse.quote(message_text.strip())
        return f"https://wa.me/{clean_phone}?text={encoded_text}"

    @classmethod
    def generate_handoff_payload(
        cls,
        website: Website,
        session_id: str,
        visitor_id: str,
        last_user_message: str,
    ) -> dict:
        """
        Generates complete WhatsApp handoff metadata and URL for the active website & session.
        """
        settings = website.settings
        if not settings or not settings.enable_whatsapp or not settings.whatsapp_number:
            return {
                "is_enabled": False,
                "handoff_url": None,
                "prefilled_message": None,
                "clean_phone": None,
            }

        store_name = website.name or "Store"
        prefilled_msg = cls.format_message_template(
            template=settings.whatsapp_custom_message,
            store_name=store_name,
            visitor_id=visitor_id,
            session_id=session_id,
            last_inquiry=last_user_message,
        )

        clean_phone = cls.normalize_phone_number(settings.whatsapp_number)
        handoff_url = cls.build_handoff_url(settings.whatsapp_number, prefilled_msg)

        return {
            "is_enabled": True,
            "handoff_url": handoff_url,
            "prefilled_message": prefilled_msg,
            "clean_phone": clean_phone,
            "trigger": settings.whatsapp_handoff_trigger or "ON_ESCALATION",
        }
