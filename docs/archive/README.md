# docs/archive/ — 历史 benchmark 产物

本目录存放**被后续版本取代的运行产物**，仅作追溯用；当前权威结果见 [`../README.md`](../README.md)。
所有文件经 `git mv` 迁入，完整历史可在 git log 中追溯。

## mmbv v1 / v2 早期线（被 `../results/benchmark_mmbv_final*` + gpt4judge/official_agg 取代，2026-07 迁入）

| 文件 | Phase | 说明 |
|---|---|---|
| `benchmark_mmbv.{json,md}` + `benchmark_mmbv_analysis.md` | 13 | v1 时代 mmbv 150 题 runs=1（vlm_direct 1.447 > agent 1.053；文首有取代横幅） |
| `benchmark_mmbv_v2.{json,md}` + `benchmark_mmbv_v2_analysis.md` | 14 | v2 早期 runs=1（agent_v2 1.933；被 runs=3 收官取代；文首有取代横幅） |
| `interview_pitch.md` | ~10 | v1 时代面试叙事稿（数字全过时），被 `../reviews/project_review_202607.md` §4 面试准备包取代 |

## v1 cooking/test1 线（被 mmbv v2 线取代）

| 文件 | Phase | 说明 |
|---|---|---|
| `benchmark_results.{json,md}` | ~6 | 最早 test1.mp4 v1 runs=1（vlm_direct 0.540 > agent 0.360） |
| `benchmark_v2_results.md` / `benchmark_v2_analysis.md` | 7 | cooking.mp4 "v2 QA set"（注意：名字带 v2 但属 **v1 agent 线**）；agent temporal 0.600 |
| `benchmark_final.{json,md}` | 7 | cooking.mp4 v1 runs=3 终版（agent 0.313） |

## v1 AGQA / 英文迁移线（被 `benchmark_v2_agqa` 取代）

| 文件 | Phase | 说明 |
|---|---|---|
| `benchmark_agqa.{json,md}` | ~10 | 中文 AGQA v1 runs=3（agent 0.364 > vlm 0.326，曾是面试稿主数字） |
| `benchmark_en_smoke.{json,md}` | 12 | 英文管线 2 视频冒烟；仍被 `../analysis/em_vs_agent_analysis.md` 引用为 EM 错配铁证 |
| `benchmark_en_llmjudge.{json,md}` | 12 | 英文 AGQA LLM-judge runs=1 |

## token 记账线（结论已并入 v2_agqa 与 project_review）

| 文件 | Phase | 说明 |
|---|---|---|
| `benchmark_tokens_smoke.{json,md}` | 12 | 真实用量口径冒烟（退役了旧"1/4 token"口径） |
| `benchmark_tokens_full.{json,md}` | 12 | AGQA 70 题 token 诊断全量 |

## smoke / 被否证实验（负面结果证据，论文可引用）

| 文件 | Phase | 说明 |
|---|---|---|
| `benchmark_verbose_smoke.{json,md}` | 12 | verbose 模式冒烟 |
| `benchmark_mmbv_v2_routed.{json,md}` | 14 | **oracle 路由上界**——否证 routing 杠杆的原始证据（负结果本身有价值，论文"被否证的方案"章节素材） |
