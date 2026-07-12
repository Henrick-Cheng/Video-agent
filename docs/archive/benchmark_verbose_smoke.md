# Benchmark Results

> Video: `2 videos`  |  Benchmark: `benchmarks/agqa_en_smoke.json`  |  Runs: 1  |  Generated: 2026-06-05 05:25

## Overall Accuracy

| Method | Acc · LLM-judge (0/0.5/1) | Avg Tool Calls | Avg Time (s) | Est. Tokens/Q |
|--------|----|----------------|--------------|---------------|
| **agent** | 0.250 ± 0.000 | 2.9 | 19.0 | 2252 |
| **vlm_direct** | 0.125 ± 0.000 | — | 3.5 | 6122 |

## Per-Category Accuracy — LLM-judge (0/0.5/1)

| Category | agent | vlm_direct |
|----------|---------|---------|
| open | 0.000±0.000 | 0.000±0.000 |
| duration | 0.500±0.000 | 0.000±0.000 |
| binary | 0.500±0.000 | 0.500±0.000 |
| sequencing | 0.000±0.000 | 0.000±0.000 |

## Per-Video Accuracy — LLM-judge (0/0.5/1)

| Video | agent | vlm_direct |
|-------|------|------|
| 03PRW.mp4 | 0.000 | 0.000 |
| 02DPI.mp4 | 0.500 | 0.250 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM
- **LLM-judge**: `qwen-plus-latest` scores 0 / 0.5 / 1 against `key_facts` (partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)
- Each method ran 1 independent trials; mean ± std reported over trials