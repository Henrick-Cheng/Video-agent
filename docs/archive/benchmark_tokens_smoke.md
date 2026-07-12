# Benchmark Results

> Video: `2 videos`  |  Benchmark: `benchmarks/agqa_en_smoke.json`  |  Runs: 1  |  Generated: 2026-06-12 02:24

## Overall Accuracy

| Method | Acc · LLM-judge (0/0.5/1) | Acc · exact-match | Avg Tool Calls | Avg Time (s) | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----|----------------|--------------|------|------|------|
| **agent** | 0.188 ± 0.000 | 0.250 ± 0.000 | 2.2 | 9.3 | 7154 | 1803 | 8957 |
| **vlm_direct** | 0.125 ± 0.000 | 0.125 ± 0.000 | — | 2.9 | 639 | — | 639 |

## Per-Category Accuracy — LLM-judge (0/0.5/1)

| Category | agent | vlm_direct |
|----------|---------|---------|
| open | 0.000±0.000 | 0.000±0.000 |
| duration | 0.250±0.000 | 0.000±0.000 |
| binary | 0.500±0.000 | 0.500±0.000 |
| sequencing | 0.000±0.000 | 0.000±0.000 |

## Per-Category Accuracy — exact-match

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
| 02DPI.mp4 | 0.375 | 0.250 |

## Per-Video Accuracy — exact-match

| Video | agent | vlm_direct |
|-------|------|------|
| 03PRW.mp4 | 0.250 | 0.000 |
| 02DPI.mp4 | 0.250 | 0.250 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM
- **Token accounting**: all counts are real API-reported `usage` summed over every call the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully counted; VL calls include image tokens in prompt_tokens). No estimates. **Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the one-time scene-graph build over that video's questions (vlm_direct has no prebuild). Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted
- **Break-even vs vlm_direct**: none — agent marginal cost (7154 tokens/Q) ≥ vlm_direct (639 tokens/Q), so the 7212-token prebuild never pays back at this question volume
- **LLM-judge**: `qwen-plus-latest` scores 0 / 0.5 / 1 against `key_facts` (partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)
- **exact-match**: strict normalized EM (1/0) against `_source.en_answer`; binary uses the first yes/no, others require normalized equality (length-guarded). Verbose answers (e.g. the ReAct agent) are reduced to their canonical short form by a deterministic extraction step before EM. NOTE: extraction is unreliable on open/'X or Y' questions (see docs/em_vs_agent_analysis.md) — treat non-binary EM as a conservative reference
- Each method ran 1 independent trials; mean ± std reported over trials