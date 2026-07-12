# Benchmark Results

> Video: `data/videos/cooking.mp4`  |  Benchmark: `benchmarks/cn_video_qa_v2.json`  |  Runs: 3  |  Generated: 2026-05-17 01:28 (agent / rag_only) · 2026-05-17 11:09 (vlm_direct, re-measured)

## Overall Accuracy

| Method | Accuracy (mean ± std) | Avg Tool Calls | Avg Time (s) | Est. Tokens/Q |
|--------|----------------------|----------------|--------------|---------------|
| **agent** | 0.313 ± 0.019 | 3.6 | 36.8 | 1383 |
| **rag_only** | 0.040 ± 0.033 | — | 4.5 | 1235 |
| **vlm_direct** | 0.373 ± 0.009 | — | 30.1 | 6039 |

## Per-Category Accuracy

| Category | agent | rag_only | vlm_direct |
|----------|---------|---------|---------|
| 物体识别 | 0.367±0.125 | 0.067±0.047 | 0.600±0.000 |
| 实体属性 | 0.333±0.125 | 0.033±0.047 | 0.500±0.000 |
| 关系推理 | 0.267±0.047 | 0.067±0.047 | 0.267±0.047 |
| 时序推理 | 0.467±0.170 | 0.000±0.000 | 0.500±0.000 |
| 计数/出现 | 0.133±0.047 | 0.033±0.047 | 0.000±0.000 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 uniform frames spanning the whole video, sends raw frames + question directly to VLM
- Judge: `qwen-plus-latest` LLM-as-Judge, scores 0 / 0.5 / 1 against `key_facts`
- Each method ran 3 independent trials; mean ± std reported

### Methodology correction (2026-05-17)

The `vlm_direct` column was **re-measured** after fixing a confound in the benchmark
harness. Previously `vlm_direct` sampled its 4 frames from the agent's pre-built
scene-graph frame cache, so its inputs silently depended on `perception.keyframe_count`
(an agent-side knob). It now extracts its own uniform frames, independent of any
agent config, and over-samples then sub-selects to span the full video — guarding
against the OpenCV last-frame decode failure that otherwise front-loaded the sample.

`agent` and `rag_only` are unaffected by this fix (it lives entirely inside the
`_answer_vlm_direct` code path) and retain their 2026-05-17 01:28 numbers.

Effect of the fix on `vlm_direct`: overall 0.293 → **0.373**; the earlier 0.293 was
itself a measurement artifact of the buggy frame coupling.
