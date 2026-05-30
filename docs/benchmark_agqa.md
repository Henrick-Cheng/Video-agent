# Benchmark Results

> Video: `10 videos`  |  Benchmark: `benchmarks/agqa_zh_small.json`  |  Runs: 3  |  Generated: 2026-05-30 06:56

## Overall Accuracy

| Method | Accuracy (mean ± std) | Avg Tool Calls | Avg Time (s) | Est. Tokens/Q |
|--------|----------------------|----------------|--------------|---------------|
| **agent** | 0.364 ± 0.015 | 4.5 | 24.4 | 1368 |
| **rag_only** | 0.186 ± 0.031 | — | 4.0 | 838 |
| **vlm_direct** | 0.326 ± 0.007 | — | 4.5 | 6041 |

## Per-Category Accuracy

| Category | agent | rag_only | vlm_direct |
|----------|---------|---------|---------|
| open | 0.206±0.068 | 0.063±0.022 | 0.198±0.011 |
| duration | 0.318±0.064 | 0.061±0.043 | 0.152±0.021 |
| binary | 0.514±0.111 | 0.431±0.098 | 0.444±0.010 |
| sequencing | 0.381±0.135 | 0.048±0.034 | 0.452±0.034 |

## Per-Video Accuracy

| Video | agent | rag_only | vlm_direct |
|-------|------|------|------|
| 03PRW.mp4 | 0.095 | 0.000 | 0.071 |
| 02DPI.mp4 | 0.381 | 0.000 | 0.143 |
| 07BSH.mp4 | 0.429 | 0.476 | 0.429 |
| 00607.mp4 | 0.714 | 0.524 | 0.714 |
| 06LBQ.mp4 | 0.524 | 0.000 | 0.333 |
| 00T1E.mp4 | 0.286 | 0.333 | 0.286 |
| 02SKC.mp4 | 0.286 | 0.095 | 0.571 |
| 07QNG.mp4 | 0.405 | 0.000 | 0.262 |
| 01THT.mp4 | 0.286 | 0.143 | 0.286 |
| 015XE.mp4 | 0.238 | 0.286 | 0.167 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM
- Judge: `qwen-plus-latest` LLM-as-Judge, scores 0 / 0.5 / 1 against `key_facts`
- Each method ran 3 independent trials; mean ± std reported