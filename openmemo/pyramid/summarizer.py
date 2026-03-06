"""
Summarizer for Memory Pyramid tier promotion.

Default implementation uses simple extractive summarization.
Can be replaced with LLM-based summarizer for better quality.
"""

from typing import List


class Summarizer:
    def summarize(self, cells: List[dict], max_length: int = 200) -> str:
        if not cells:
            return ""

        contents = [c.get("content", "") for c in cells if c.get("content")]

        if not contents:
            return ""

        if len(contents) == 1:
            return contents[0][:max_length]

        combined = " | ".join(contents)
        if len(combined) <= max_length:
            return combined

        sentences = []
        for c in contents:
            parts = c.replace(". ", ".\n").split("\n")
            sentences.extend(p.strip() for p in parts if p.strip())

        result = []
        current_len = 0
        for s in sentences:
            if current_len + len(s) > max_length:
                break
            result.append(s)
            current_len += len(s)

        return " ".join(result) if result else combined[:max_length]
