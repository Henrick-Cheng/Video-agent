# docs/ 索引

本目录只保留 **v2 线（lazy 3-layer memory + confidence loop）的权威文件与论文材料**。
历史/被取代的 benchmark 产物统一放在 [`archive/`](archive/README.md)。

## 权威结果（论文取数源，勿改动）

| 文件 | 说明 |
|---|---|
| `benchmark_mmbv_final_analysis.md` | **MMBench-Video runs=3 权威报告**（agent_v2 1.984±0.101 > vlm_transcript 1.727 > vlm_direct 1.478）——论文第 5 章唯一取数源 |
| `benchmark_mmbv_final.{json,md}` | 上述结果的原始逐题记录 / 标准报表（case study 原始 trace；`scripts/rejudge_gpt4.py` 默认输入） |
| `benchmark_v2_agqa.{json,md}` | v2 英文 AGQA 门禁结果（duration 0.682） |
| `annotation_audit.json` | n=30 标注审计（97% gold 有依据），`scripts/annotation_audit.py` 产物 |

## 对照与分析（README 链接）

| 文件 | 说明 |
|---|---|
| `benchmark_mmbv_v2_analysis.md` | v2 runs=1 细粒度分析 |
| `benchmark_mmbv_v2.{json,md}` | v2 runs=1 原始记录（v2_analysis 的数据源） |
| `benchmark_mmbv_analysis.md` | v1 MMBench-Video 交叉分析（v1 对照） |
| `benchmark_mmbv.{json,md}` | v1 MMBench-Video 原始记录（v2 分析中的 v1 基线列） |
| `em_vs_agent_analysis.md` | EM 指标与生成式 Agent 的错配分析（评测方法论，`run_benchmark.py` 注释引用） |

## 架构与综述

| 文件 | 说明 |
|---|---|
| `architecture.md` | 系统架构详解（2026-07-14 已同步 v2；文末含 v1→v2 对比表；论文第 4 章素材） |
| `architecture_review_202607.md` | 2026-07 架构评审（论文第 6 章素材） |
| `project_review_202607.md` | 2026-07 全仓综述；**§1.4 = 简历/面试用权威数字**；§1.5 = 系统设计审核（设计强项 + 设计债） |
| `thesis_outline.md` | 论文大纲 + 材料映射表（定义各章取数源） |
| `progress.md` | Phase 1–15 编年演进日志（历史叙述中的旧文件路径不回改） |
| `ai_dev_workflow.md` | AI 辅助开发工作流手册（从本项目实践提炼，可复用于新项目；面试 Q9/Q16/Q17 素材） |
| `interview_pitch.md` | 面试叙事稿（⚠️ 数字为 v1 时代，待按 project_review §1.4 重写） |
