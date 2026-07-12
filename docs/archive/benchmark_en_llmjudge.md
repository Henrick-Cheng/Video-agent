# Benchmark Results

> Video: `10 videos`  |  Benchmark: `benchmarks/agqa_en_small.json`  |  Runs: 1  |  Generated: 2026-06-06 00:14

## Overall Accuracy

| Method | Acc · LLM-judge (0/0.5/1) | Avg Tool Calls | Avg Time (s) | Est. Tokens/Q |
|--------|----|----------------|--------------|---------------|
| **agent** | 0.436 ± 0.000 | 3.4 | 23.2 | 2860 |
| **rag_only** | 0.321 ± 0.000 | — | 3.7 | 980 |
| **vlm_direct** | 0.450 ± 0.000 | — | 3.4 | 6188 |

## Per-Category Accuracy — LLM-judge (0/0.5/1)

| Category | agent | rag_only | vlm_direct |
|----------|---------|---------|---------|
| open | 0.333±0.000 | 0.167±0.000 | 0.476±0.000 |
| duration | 0.500±0.000 | 0.273±0.000 | 0.318±0.000 |
| binary | 0.625±0.000 | 0.562±0.000 | 0.542±0.000 |
| sequencing | 0.214±0.000 | 0.179±0.000 | 0.357±0.000 |

## Per-Video Accuracy — LLM-judge (0/0.5/1)

| Video | agent | rag_only | vlm_direct |
|-------|------|------|------|
| 03PRW.mp4 | 0.286 | 0.000 | 0.286 |
| 02DPI.mp4 | 0.429 | 0.143 | 0.143 |
| 07BSH.mp4 | 0.714 | 0.929 | 0.571 |
| 00607.mp4 | 0.714 | 0.571 | 0.571 |
| 06LBQ.mp4 | 0.571 | 0.143 | 0.857 |
| 00T1E.mp4 | 0.429 | 0.429 | 0.571 |
| 02SKC.mp4 | 0.286 | 0.357 | 0.143 |
| 07QNG.mp4 | 0.357 | 0.000 | 0.571 |
| 01THT.mp4 | 0.286 | 0.500 | 0.500 |
| 015XE.mp4 | 0.286 | 0.143 | 0.286 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM
- **LLM-judge**: `qwen-plus-latest` scores 0 / 0.5 / 1 against `key_facts` (partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)
- Each method ran 1 independent trials; mean ± std reported over trials