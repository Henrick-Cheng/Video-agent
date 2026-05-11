"""
Closed-vocabulary relation labels for the Video Agent scene graph.

The VLM prompt instructs the model to select relations from this list,
which keeps the graph schema consistent and deduplication reliable.

50 verbs covering the most common human-object and person-person interactions
in real-world video (surveillance, daily activity, social scene, traffic, etc.).
"""
from __future__ import annotations

RELATION_VOCAB: list[str] = [
    # ── 持有 / 操作 ────────────────────────────────────────────────────────
    "持有",    # holding (general possession)
    "拿着",    # carrying in hand
    "携带",    # carrying on body / bag
    "使用",    # using a tool / device
    "操作",    # operating a machine / panel

    # ── 视觉 / 注意 ────────────────────────────────────────────────────────
    "看向",    # looking at (direction)
    "注视",    # gazing at (sustained attention)
    "观察",    # observing / watching carefully
    "指向",    # pointing at

    # ── 移动 ──────────────────────────────────────────────────────────────
    "走向",    # walking toward
    "跑向",    # running toward
    "靠近",    # approaching / getting closer
    "远离",    # moving away from
    "跟随",    # following
    "追赶",    # chasing
    "穿过",    # crossing / passing through
    "经过",    # passing by
    "进入",    # entering
    "离开",    # leaving / exiting

    # ── 交互 / 社交 ────────────────────────────────────────────────────────
    "对话",    # talking / conversing with
    "给予",    # giving to
    "接收",    # receiving from
    "协作",    # cooperating with
    "对峙",    # confronting / facing off
    "帮助",    # helping
    "躲避",    # avoiding / evading

    # ── 力 / 接触 ─────────────────────────────────────────────────────────
    "推开",    # pushing away
    "推动",    # pushing (object)
    "拉拽",    # pulling
    "抓住",    # grabbing / seizing
    "放下",    # putting down
    "举起",    # lifting
    "触碰",    # touching
    "阻挡",    # blocking

    # ── 姿态 / 位置 ────────────────────────────────────────────────────────
    "坐在",    # sitting on / in
    "站在",    # standing on / at
    "躺在",    # lying on
    "靠着",    # leaning against
    "攀爬",    # climbing

    # ── 物体操控 ──────────────────────────────────────────────────────────
    "打开",    # opening (door, box, etc.)
    "关闭",    # closing
    "骑乘",    # riding (bicycle, horse, etc.)
    "驾驶",    # driving (vehicle)

    # ── 空间关系 ──────────────────────────────────────────────────────────
    "位于",    # located at / in
    "停在",    # stopped at / parked at
    "面向",    # facing toward
    "背对",    # facing away from

    # ── 物体间 ────────────────────────────────────────────────────────────
    "放置于",  # placed on / in
    "连接",    # connected to
    "属于",    # belonging to / owned by
]

# Convenience set for O(1) membership test
RELATION_VOCAB_SET: frozenset[str] = frozenset(RELATION_VOCAB)


def is_valid_relation(rel: str) -> bool:
    """Return True if rel is in the closed vocabulary."""
    return rel in RELATION_VOCAB_SET
