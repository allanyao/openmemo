"""
Skill Extractor - Identifies skill-worthy patterns from memory.
"""

from typing import List


class SkillExtractor:
    def __init__(self, min_frequency: int = 3):
        self.min_frequency = min_frequency

    def extract_patterns(self, cells: List[dict]) -> List[dict]:
        word_pairs = {}

        for cell in cells:
            content = cell.get("content", "").lower()
            words = content.split()

            for i in range(len(words) - 1):
                pair = f"{words[i]} {words[i+1]}"
                if pair not in word_pairs:
                    word_pairs[pair] = 0
                word_pairs[pair] += 1

        patterns = []
        for pair, count in word_pairs.items():
            if count >= self.min_frequency:
                patterns.append({
                    "pattern": pair,
                    "frequency": count,
                })

        patterns.sort(key=lambda x: x["frequency"], reverse=True)
        return patterns
