# Benchmark Results

> Video: `10 videos`  |  Benchmark: `benchmarks/agqa_en_small.json`  |  Runs: 1  |  Generated: 2026-06-12 21:51

## Overall Accuracy

| Method | Acc · LLM-judge (0/0.5/1) | Acc · exact-match | Avg Tool Calls | Avg Time (s) | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----|----------------|--------------|------|------|------|
| **agent_v2** | 0.436 ± 0.000 | 0.386 ± 0.000 | 1.3 | 18.5 | 5190 | 181 | 5372 |

## Per-Category Accuracy — LLM-judge (0/0.5/1)

| Category | agent_v2 |
|----------|---------|
| open | 0.190±0.000 |
| duration | 0.682±0.000 |
| binary | 0.625±0.000 |
| sequencing | 0.286±0.000 |

## Per-Category Accuracy — exact-match

| Category | agent_v2 |
|----------|---------|
| open | 0.190±0.000 |
| duration | 0.273±0.000 |
| binary | 0.625±0.000 |
| sequencing | 0.357±0.000 |

## Per-Video Accuracy — LLM-judge (0/0.5/1)

| Video | agent_v2 |
|-------|------|
| 03PRW.mp4 | 0.286 |
| 02DPI.mp4 | 0.143 |
| 07BSH.mp4 | 1.000 |
| 00607.mp4 | 0.714 |
| 06LBQ.mp4 | 0.143 |
| 00T1E.mp4 | 0.571 |
| 02SKC.mp4 | 0.571 |
| 07QNG.mp4 | 0.429 |
| 01THT.mp4 | 0.357 |
| 015XE.mp4 | 0.143 |

## Per-Video Accuracy — exact-match

| Video | agent_v2 |
|-------|------|
| 03PRW.mp4 | 0.143 |
| 02DPI.mp4 | 0.143 |
| 07BSH.mp4 | 0.857 |
| 00607.mp4 | 0.857 |
| 06LBQ.mp4 | 0.143 |
| 00T1E.mp4 | 0.571 |
| 02SKC.mp4 | 0.429 |
| 07QNG.mp4 | 0.286 |
| 01THT.mp4 | 0.286 |
| 015XE.mp4 | 0.143 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **agent_v2**: Lazy-memory agent — per-video init is only a sparse-frame summary + local ASR transcript; the agent then decides at runtime which time windows to explore (explore_segment builds dense captions + indexed triplets on demand), with a confidence-driven loop (rate 1-3, ≤2 explores/round, ≤3 rounds)
- **agent_tiered**: Cost-aware agent — scene graph (or its summary, when >30 triplets) injected into context; the model decides at runtime whether to answer directly (one LLM call) or escalate to query/inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples N frames (default 4, see --vlm-frames), sends raw frames + question directly to VLM
- **Prebuild frame budget**: duration-adaptive — one frame per ~15s, clamped to [8, 24] (Charades-length clips stay at the historical 8)
- **Token accounting**: all counts are real API-reported `usage` summed over every call the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully counted; VL calls include image tokens in prompt_tokens). No estimates. **Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the one-time scene-graph build over that video's questions (vlm_direct has no prebuild). Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted
- **LLM-judge**: `qwen-plus-latest` scores 0 / 0.5 / 1 against `key_facts` (partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)
- **exact-match**: strict normalized EM (1/0) against `_source.en_answer`; binary uses the first yes/no, others require normalized equality (length-guarded). Verbose answers (e.g. the ReAct agent) are reduced to their canonical short form by a deterministic extraction step before EM. NOTE: extraction is unreliable on open/'X or Y' questions (see docs/analysis/em_vs_agent_analysis.md) — treat non-binary EM as a conservative reference
- Each method ran 1 independent trials; mean ± std reported over trials