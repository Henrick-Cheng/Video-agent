# docs/ 索引

按用途分四个子目录 + 根目录活文档。历史/被取代的产物统一在 [`archive/`](archive/README.md)。

## 根目录（长期维护的活文档）

| 文件 | 说明 |
|---|---|
| `progress.md` | Phase 1–16 编年演进日志（约定：历史叙述中的旧路径/旧表述不回改） |
| `architecture.md` | 系统架构详解（v2；文末含 v1→v2 对比表；论文第 4 章素材） |
| `ai_dev_workflow.md` | AI 辅助开发工作流手册（从本项目实践提炼，可复用于新项目；面试 Q9/Q16/Q17 素材） |

## results/ — 评测产物（当前权威，勿改动）

| 文件 | 说明 |
|---|---|
| `benchmark_mmbv_final_gpt4judge.{json,md}` | **论文引用口径**：gpt-4-turbo 官方判分 + 官方多标签聚合（1.978/1.713/1.491，含论文版式表） |
| `benchmark_mmbv_final_official_agg.{json,md}` | qwen-max 判分 + 官方多标签聚合（稳健性对照，总分与 gpt 口径差 <0.015） |
| `benchmark_mmbv_final.{json,md}` | runs=3 收官运行的原始逐题记录 / 原始报表（⚠️ md 维度表为旧单标签口径，已被上两份取代；json 为 case study trace 与 `scripts/rejudge_gpt4.py`、`scripts/reaggregate_mmbv.py` 的默认输入） |
| `benchmark_mmbv_final.rejudge_gpt-4-turbo.{json,summary.json}` | gpt-4-turbo 重判原始分 + 一致率摘要（judge 噪声带 0.76–0.81） |
| `benchmark_v2_agqa.{json,md}` | v2 英文 AGQA 门禁结果（duration 0.682） |
| `annotation_audit.json` | n=30 标注审计（97% gold 有依据），`scripts/annotation_audit.py` 产物 |

## analysis/ — 现行分析与方法论

| 文件 | 说明 |
|---|---|
| `benchmark_mmbv_final_analysis.md` | **MMBench-Video 收官分析**（叙事取数源：抗噪/归因/舒适区/关键维度/披露；维度数字已同步官方多标签口径） |
| `em_vs_agent_analysis.md` | EM 指标与生成式 Agent 的错配分析（评测方法论，`run_benchmark.py` 注释引用） |

## reviews/ — 审核与规划（论文 / 求职）

| 文件 | 说明 |
|---|---|
| `project_review_202607.md` | 2026-07 全仓综述；**§1.4 = 简历/面试用权威数字**；§1.5 = 系统设计审核；§4 = 面试准备包 |
| `architecture_review_202607.md` | 2026-07 架构评审（论文第 6 章素材） |
| `thesis_outline.md` | 论文大纲 + 材料映射表（定义各章取数源） |

## archive/ — 历史归档

被后续版本取代的运行记录与文稿（v1 时代 mmbv 线、v2 runs=1 线、v1 面试稿等），
git mv 迁入、历史可溯，详见 [`archive/README.md`](archive/README.md)。
