import re
from typing import List, Optional, Tuple
from app.services.rag.text_cleaner import TextCleaner


class ChunkItem:
    def __init__(self, chunk_index: int, content: str, token_count: int):
        self.chunk_index = chunk_index
        self.content = content
        self.token_count = token_count

    def to_dict(self):
        return {
            "chunk_index": self.chunk_index,
            "content": self.content,
            "token_count": self.token_count,
        }


class ChunkQualityFilter:
    """Filters out low-quality chunks (navigation, menus, boilerplate)."""

    # Patterns that indicate navigation/boilerplate content
    NAVIGATION_PATTERNS = [
        r'^(home|shop|about|contact|blog|faq|login|register|cart|checkout|account)\s*$',
        r'^(add to basket|add to cart|buy now|view cart|wishlist)\s*$',
        r'^(previous|next|back|forward|page \d+|loading)\s*$',
        r'^\d+\s*$',  # Just a number
        r'^(search|menu|close|open|expand|collapse)\s*$',
    ]

    # Low-value content indicators
    LOW_VALUE_PATTERNS = [
        r'^(sale|new|trending|popular|featured)\s*$',
        r'^(login|sign in|sign up|register|forgot password)\s*$',
        r'^(terms|privacy|policy|refund|shipping)\s*$',
        r'^(copyright|all rights reserved)\s*$',
    ]

    @classmethod
    def _is_navigation(cls, text: str) -> bool:
        text = text.strip().lower()
        if len(text) < 3:
            return True
        for pattern in cls.NAVIGATION_PATTERNS + cls.LOW_VALUE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _has_meaningful_content(cls, chunk: str) -> bool:
        """Check if chunk has actual product/content info, not just labels."""
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        if not lines:
            return False

        # Count lines that look like actual content (have spaces, sentences, etc.)
        content_lines = 0
        for line in lines:
            # Skip navigation-like lines
            if cls._is_navigation(line):
                continue
            # Count lines with multiple words or sentences
            if len(line.split()) >= 3 or re.search(r'[.!?]', line):
                content_lines += 1

        # At least 30% of lines should be real content
        return content_lines >= max(1, len(lines) * 0.3)

    @classmethod
    def score_chunk(cls, chunk: str) -> float:
        """Score chunk quality from 0.0 (bad) to 1.0 (good)."""
        if not chunk or not chunk.strip():
            return 0.0

        score = 1.0

        # Penalize very short chunks
        word_count = len(chunk.split())
        if word_count < 10:
            score -= 0.5
        elif word_count < 20:
            score -= 0.2

        # Penalize chunks with too many short lines (navigation-like)
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        nav_lines = sum(1 for l in lines if cls._is_navigation(l))
        if lines:
            nav_ratio = nav_lines / len(lines)
            if nav_ratio > 0.5:
                score -= 0.5
            elif nav_ratio > 0.3:
                score -= 0.2

        # Penalize chunks that look like category listings
        if re.match(r'^[\w\s,&]+$', chunk) and not re.search(r'[.!?]', chunk):
            # Looks like a list of categories (no sentences)
            score -= 0.3

        # Boost chunks with product descriptions (have sentences, specs, prices)
        if re.search(r'\d+[cm]m', chunk, re.IGNORECASE):  # Measurements
            score += 0.1
        if re.search(r'£|\$|price', chunk, re.IGNORECASE):  # Prices
            score += 0.1
        if re.search(r'(safety|distance|effect|colour|color)', chunk, re.IGNORECASE):  # Product specs
            score += 0.1

        # Boost chunks with substantial paragraphs
        has_paragraph = any(len(l) > 50 for l in lines)
        if has_paragraph:
            score += 0.1

        return max(0.0, min(1.0, score))

    @classmethod
    def filter_chunks(cls, chunks: List[str], min_score: float = 0.4) -> List[Tuple[str, float]]:
        """Filter chunks by quality. Returns list of (chunk, score) tuples."""
        scored = [(chunk, cls.score_chunk(chunk)) for chunk in chunks]
        return [(chunk, score) for chunk, score in scored if score >= min_score]


class DocumentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150, min_quality: float = 0.4):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_quality = min_quality

    @staticmethod
    def estimate_tokens(text: str) -> int:
        words = len(text.split())
        return max(1, int(words * 1.33))

    def split_text(self, text: str) -> List[str]:
        clean_text = TextCleaner.clean(text)
        if not clean_text:
            return []

        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= self.chunk_size:
                        current_chunk = f"{current_chunk} {sent}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                            current_chunk = f"{overlap_text} {sent}".strip()
                        else:
                            words = sent.split(" ")
                            temp = ""
                            for w in words:
                                if len(temp) + len(w) + 1 <= self.chunk_size:
                                    temp = f"{temp} {w}".strip()
                                else:
                                    if temp:
                                        chunks.append(temp)
                                    temp = w
                            if temp:
                                current_chunk = temp
            else:
                if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                        overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                        current_chunk = f"{overlap_text}\n\n{para}".strip()
                    else:
                        current_chunk = para

        if current_chunk and current_chunk not in chunks:
            chunks.append(current_chunk)

        return chunks

    def chunk_document(self, text: str) -> List[ChunkItem]:
        raw_chunks = self.split_text(text)

        # Filter by quality
        filtered = ChunkQualityFilter.filter_chunks(raw_chunks, self.min_quality)

        chunk_items: List[ChunkItem] = []
        for idx, (chunk_text, _score) in enumerate(filtered):
            tokens = self.estimate_tokens(chunk_text)
            chunk_items.append(ChunkItem(chunk_index=idx, content=chunk_text, token_count=tokens))
        return chunk_items
