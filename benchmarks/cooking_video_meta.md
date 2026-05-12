# cooking.mp4 — Video Content Analysis

> Analyzed: 2026-05-12 | VLM: qwen-vl-plus-latest | Frames: 15 uniform (t=0–202s)

## Basic Info

| Field | Value |
|-------|-------|
| Duration | ~202 seconds (3m 22s) |
| Dish | 红烧肉 (Red-Braised Pork Belly) |
| Video style | Short-form cooking tutorial (Douyin-style) |
| Frame interval | ~14.4s |

## Ingredients Identified

| Ingredient | Chinese | First Seen (approx.) | Role |
|-----------|---------|----------------------|------|
| Pork belly | 五花肉 | t=0s | Main protein |
| Rock sugar | 冰糖 | t=57s | Caramelizing (炒糖色) |
| Soy sauce | 酱油 | t=72–86s | Flavoring & color |
| Cooking wine | 料酒 | t=173s | Deglazing / flavor |
| Star anise | 八角 | t=159s | Spice (added from bowl) |
| Bay leaf | 香叶 | t=159s | Spice (added from bowl) |
| Dried chili | 干辣椒 | t=159s | Spice (added from bowl) |
| Scallion | 葱 | t=0s (blanching), t=144s (braise), t=187s (garnish) | Multi-use |
| Ginger | 姜 | t=0s (blanching) | Blanching deodorizer |
| Water | 水 | t=86s | Braising liquid |
| Sugar | 糖 | t=173s | Additional sweetener |
| Cinnamon stick | 桂皮 | t=173s | Spice |

## Cookware Used (in order of appearance)

1. **平底锅** (flat pan) — blanching pork belly with ginger + scallion
2. **砧板 + 菜刀** (cutting board + cleaver) — cutting blanched pork into cubes
3. **炒锅** (wok) — caramelizing rock sugar → stir-frying pork pieces → adding soy sauce + water
4. **砂锅** (clay pot) — slow braising with spices, low heat until tender
5. 汤勺 (ladle), 筷子 (chopsticks), 碗 (small bowl for pre-measured spices)

## Cooking Steps (Temporal Sequence)

| Phase | Time (approx.) | Action | Notes |
|-------|----------------|--------|-------|
| 1. 焯水 | t=0–14s | Whole pork belly blanched in flat pan with ginger + scallion | Deodorizing step |
| 2. 切块 | t=14–29s | Blanched pork cut into cubes on cutting board | ~3–4cm pieces |
| 3. 炒糖色 | t=57–72s | Rock sugar caramelized in wok over medium heat | Key visual step |
| 4. 下肉翻炒 | t=72–101s | Pork cubes added to wok, stir-fried until surface caramelized; soy sauce + water added | Medium heat |
| 5. 转砂锅 | t=115–130s | Pork transferred to clay pot; scallion added | |
| 6. 加香料 | t=144–159s | Dried chili, star anise, bay leaf (from pre-measured small bowl) added | |
| 7. 慢炖 | t=159–187s | Clay pot covered, low heat slow braise | Long phase |
| 8. 出锅 | t=187–202s | Lid opened, red-braised pork revealed; chopstick close-up shows tender texture | Garnished with scallion |

## Subtitles (Observed)

Subtitles are **comedic/commentator-style**, NOT recipe instructions. They cannot directly answer cooking-specific questions.

| Time (approx.) | Subtitle Text | Note |
|----------------|---------------|------|
| t≈0s | 红烧肉 | Title card |
| t≈14s | 公文包 | Irrelevant comedy subtitle |
| t≈43s | 中火 | Heat level indicator |
| t≈57–86s | 可以做冰糖葫芦 / 红烧、卤水 / 这样 | Partial descriptions, not instructional |
| t≈115–159s | 苍蝇搓手 / 不会 / 都不要 | Comedy subtitles, unrelated to steps |
| t≈187s | 红烧肉 | Dish name at reveal |

**Key finding**: Subtitles do NOT enumerate ingredients, do NOT specify sequences (e.g., which goes in first), and do NOT give counts. They are safe to leave in — vlm_direct cannot use them to cheat on the specific QA questions designed below.

## Scene Graph Sketch (Key Triplets)

```
五花肉 → 焯水于 → 平底锅
五花肉 → 切成 → 肉块
冰糖 → 炒于 → 炒锅
五花肉块 → 炒于 → 炒锅
酱油 → 加入 → 炒锅
五花肉 → 转入 → 砂锅
葱 → 加入 → 砂锅
八角/香叶/干辣椒 → 加入 → 砂锅
砂锅 → 小火慢炖 → 红烧肉
红烧肉 → 撒上 → 葱花
```

## Anti-Subtitle QA Design Principles

Questions for cn_video_qa_v2.json are designed to:
1. Ask about **specific sequences** (subtitles never state "A before B")
2. Ask about **co-occurrence** (which ingredients went in together)
3. Ask about **multiple cookware** (requires watching multiple phases)
4. Ask about **precise counts** of ingredients/tools/phases
5. Avoid questions about text visible in frames (dish names, heat labels)
