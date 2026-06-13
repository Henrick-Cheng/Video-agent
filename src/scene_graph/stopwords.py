"""
English stopwords for scene graph retrieval.

These tokens carry no semantic value for entity/relation matching and are
filtered out before scoring triplets against a query.
"""
from __future__ import annotations

STOPWORDS: frozenset[str] = frozenset([
    # Articles / determiners
    "a", "an", "the", "this", "that", "these", "those", "some", "any",
    # Auxiliary / copula verbs
    "is", "are", "was", "were", "be", "been", "being", "am",
    "do", "does", "did", "have", "has", "had",
    "will", "would", "can", "could", "shall", "should", "may", "might", "must",
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they",
    "him", "her", "them", "us", "me",
    "his", "their", "its", "our", "your", "my",
    "who", "whom", "whose", "which", "what",
    "someone", "something", "anyone", "anything",
    # Question / interrogative words
    "how", "where", "when", "why", "whether",
    # Conjunctions
    "and", "or", "but", "if", "while", "as", "than", "then",
    # Prepositions / locatives (spatial nuance lives in relations, not queries)
    "in", "on", "at", "to", "of", "for", "with", "by", "from",
    "into", "onto", "over", "under", "near", "beside", "between",
    "around", "behind", "front", "above", "below", "next",
    # Video / media specific (appear in nearly every query, no discrimination)
    "video", "frame", "frames", "scene", "image", "picture", "clip",
    # Politeness / meta
    "please", "tell",
    # Common low-signal verbs / adverbs
    "see", "seen", "show", "shows", "appear", "appears", "happen", "happens",
    "there", "here", "also", "did",
    # Quantifiers / numbers acting as fillers
    "one", "many", "much", "more", "kind", "type", "sort",
    # Punctuation
    "?", ".", "!", ",", ";", ":", "…", "-", "'s",
])

# Time expression keywords mapping surface form → canonical position tag
# Used by the retriever to extract time constraints from queries.
TIME_KEYWORDS: dict[str, str] = {
    "beginning": "start",
    "begin": "start",
    "start": "start",
    "first": "start",
    "initially": "start",
    "initial": "start",
    "end": "end",
    "ending": "end",
    "last": "end",
    "finally": "end",
    "final": "end",
    "later": "end",
    "afterward": "end",
    "afterwards": "end",
}
