import re
from typing import List, Optional
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


class DocumentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def estimate_tokens(text: str) -> int:
        words = len(text.split())
        return max(1, int(words * 1.33))

    def split_text(self, text: str) -> List[str]:
        """
        Splits text into chunks respecting paragraph and sentence boundaries.
        """
        clean_text = TextCleaner.clean(text)
        if not clean_text:
            return []

        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        # 1. Split by paragraphs
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            # If paragraph itself is larger than chunk_size, split by sentences
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= self.chunk_size:
                        current_chunk = f"{current_chunk} {sent}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            # Apply overlap from the tail of current_chunk
                            overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                            current_chunk = f"{overlap_text} {sent}".strip()
                        else:
                            # Sentence itself is longer than chunk_size, split by words
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
        chunk_items: List[ChunkItem] = []
        for idx, chunk_text in enumerate(raw_chunks):
            tokens = self.estimate_tokens(chunk_text)
            chunk_items.append(ChunkItem(chunk_index=idx, content=chunk_text, token_count=tokens))
        return chunk_items
