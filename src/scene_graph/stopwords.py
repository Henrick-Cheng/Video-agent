"""
Chinese stopwords for scene graph retrieval.

These tokens carry no semantic value for entity/relation matching and are
filtered out before scoring triplets against a query.
"""
from __future__ import annotations

STOPWORDS: frozenset[str] = frozenset([
    # Particles and auxiliaries
    "的", "了", "是", "在", "有", "和", "也", "都", "把", "被",
    "地", "得", "吗", "吧", "啊", "呢", "呀", "嗯", "哦", "嘛",
    # Question / interrogative words
    "什么", "怎么", "如何", "哪", "哪些", "哪里", "哪儿",
    "谁", "几个", "多少", "为什么", "怎样", "是否",
    # Demonstratives / deictics
    "这", "那", "这个", "那个", "这些", "那些", "这里", "那里",
    # Video / media specific (appear in nearly every query, no discrimination)
    "视频", "视频中", "视频里", "画面", "画面中", "画面里",
    "图中", "图里", "图片", "帧", "帧中",
    # Politeness / meta
    "请问", "请", "告诉", "我", "我想", "我想知道",
    # Prepositions / locatives
    "里", "中", "上", "下", "里面", "外面", "旁边", "附近",
    "前面", "后面", "左边", "右边", "之间", "周围",
    # Common auxiliary verbs / copulas
    "看", "看到", "显示", "出现", "有没有", "发生",
    # Sentence-final particles
    "？", "?", "。", ".", "！", "!", "，", ",", "、", "…",
    # Numbers acting as quantifiers
    "一个", "一", "个", "些", "种", "类",
])

# Time expression keywords mapping surface form → canonical position tag
# Used by the retriever to extract time constraints from queries.
TIME_KEYWORDS: dict[str, str] = {
    "开头": "start",
    "开始": "start",
    "最初": "start",
    "第一": "start",
    "起初": "start",
    "结尾": "end",
    "最后": "end",
    "末尾": "end",
    "结束": "end",
    "最终": "end",
    "后来": "end",
}
