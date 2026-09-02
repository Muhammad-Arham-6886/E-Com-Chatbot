import re
import unicodedata


class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # 1. Normalize unicode (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Replace non-breaking spaces and zero-width spaces
        cleaned = normalized.replace("\xa0", " ").replace("\u200b", "").replace("\r\n", "\n")

        # 3. Strip markdown link targets while preserving anchor text [Anchor Text](https://url) -> Anchor Text
        cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

        # 4. Strip markdown image tags ![alt](url) -> ""
        cleaned = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", cleaned)

        # 5. Clean markdown headers (### Header -> Header)
        cleaned = re.sub(r"^\s*#+\s*", "", cleaned, flags=re.MULTILINE)

        # 6. Clean bold/italic asterisks/underscores
        cleaned = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", cleaned)

        # 7. Normalize multiple spaces and multiple blank lines
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()
