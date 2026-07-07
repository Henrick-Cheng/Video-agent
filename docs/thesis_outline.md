# 学位论文框架与写作指南（2026-07）

> 论文语言：英文（NTU EEE MSc dissertation）。本文档：章节骨架（英文标题 + 每节写什么）+ 材料映射（仓库哪份文档喂哪章）+ 写作顺序与避坑。
> 核心主张沿用已定稿的口径（review §Q0）：**long-video multimodal evidence localization & integration** —— 不是"时序推理更强"。

## 0. 标题候选

- *Scene Graphs as Evidence Indexes: Lazy Memory and Confidence-Driven LLM Agents for Long-Video Question Answering*（推荐——把"图=索引"的立场放进标题）
- *Enhancing Long-Video Understanding via Scene-Graph-Indexed Lazy Memory and LLM Agents*（更贴近中文课题名的直译）

## 1. 章节骨架（六章 + 附录）

### Ch.1 Introduction（~8%）
- 1.1 Background：长视频问答的瓶颈——答案依赖散落在时间轴上的几秒证据；均匀采帧在 >90s 失效（写作素材：README 三句话 + Q0 白话解释）。
- 1.2 Motivation & Problem Statement：三个失败模式（盲采漏证据 / 旁白模态浪费 / 全量预处理摊不回）。
- 1.3 **Research Questions**（论文的骨；每个 RQ 在 Ch.5 有对应实验小节）：
  - RQ1：场景图作为「证据的时序索引」（而非答案来源）能否让 agent 反超直接看帧的 VLM？
  - RQ2：按需建图（lazy）相对全量预建，在成本与精度上各带来什么？
  - RQ3：增益来自多模态（ASR）还是架构本身？（归因协议）
- 1.4 Contributions（三条，对应 review §2.1）：①图的角色重定位 + lazy 逐题建图；②置信度驱动的感知预算分配（3.1 vs 8 帧）；③模态/架构归因评测协议 + 负结果留档。
- 1.5 Organization。

### Ch.2 Background & Related Work（~15%）
- 2.1 VLMs for video（直推范式与上下文限制）。
- 2.2 Video scene graphs（图像 SGG → 时序场景图；有损压缩问题的文献铺垫）。
- 2.3 LLM agents & tool use（ReAct、记忆增强 agent）。
- 2.4 **Agent-based video understanding**（重点节）：VideoAgent(ECCV'24) / VideoAgent(memory, Fan'24) / DoraemonGPT / Deep Video Discovery / VideoTree·LLoVi —— 直接展开 review §2.2 的定位表，逐个写"它做什么/本文差异"。
- 2.5 Video QA benchmarks & LLM-as-judge（MMBench-Video 官方协议、judge 偏差问题——为 Ch.5 的诚实披露埋文献依据）。

### Ch.3 A Scene-Graph-Centric Baseline and Its Empirical Diagnosis（~15%）
把 v0→v1 写成正式的"第一次迭代 + 诊断"，这是本论文最有辨识度的一章：
- 3.1 v0 fixed pipeline（感知-构图-检索-回答）与 v1 ReAct agent 设计（四工具）。
- 3.2 Diagnosis under real-usage accounting：v1 1.193 < vlm_direct 1.478；两个机制性错误——triplet 有损瓶颈（纯三元组 RAG 只保住约一半信号）、全量预建摊销不回（素材：progress.md Phase 12-13、README "为什么是 v2"）。
- 3.3 Design requirements derived（多粒度按需记忆 / caption 必须保留 / 置信度编排）——自然引出 Ch.4。

### Ch.4 Method: Lazy Three-Layer Memory & Confidence-Driven Orchestration（~22%）
- 4.1 Overview + 架构图（重绘 README mermaid 为正式矢量图）。
- 4.2 Three-layer lazy memory：L0/L1/L2 定义、构建时机表、**provenance 设计**（triplet 挂 seg:id、命中回带 caption+转写——"图是目录，证据在 caption"是本章的 thesis statement）。
- 4.3 Tools：search_memory（零成本联合检索）/ explore_segment（逐题建图）/ inspect_frame；实体命名三道防线 + 关系时窗合并（素材：builder.py、review 附录）。
- 4.4 Confidence-driven loop：自评 1-3、预算上限（≤2/轮、≤3 轮）、grounding rules（absence≠no —— HL 2.3× 的机制来源，此处先讲设计、Ch.5 给数）。
- 4.5 Implementation notes（半页到一页即可）：双后端抽象、fail-loud 契约、真实计费账本、pseudo-call 防护——工程细节点到为止，展开放 Appendix。

### Ch.5 Evaluation（~30%，全文重心）
- 5.1 Setup：MMBench-Video 150 题分层子集（seed=42，**如实声明与公开榜不可直接比**）；VLMEvalKit 0–3 judge 复刻；runs=3；真实 usage 口径；基线三件套（vlm_direct / **vlm_transcript 公平基线** / v1）。
- 5.2 Main results（RQ1）：1.984±0.101 > 1.727±0.020 > 1.478±0.025；抗噪判据 gap 0.257 > std 和 0.121。
- 5.3 Attribution（RQ3）：ASR +0.249 / 架构 +0.257 —— 论文最硬的一节。
- 5.4 Analysis by duration（舒适区 ≈90s、money chart 折线图）与 by dimension（HL 2.3×、FP-C 2×；**如实写 TR 输给基线**并解释为模态驱动——审稿人/答辩委员看到主动披露会加分）。
- 5.5 Perception budget（RQ2）：frames-touched 3.1 vs 8；81/150 零探索直答的分布。
- 5.6 Ablations & negative results：oracle routing 证伪（选择偏差）、caption 加密证伪（能力天花板）——写成"剩余差距的归因"，这是方法论亮点不是失败记录。
- 5.7 AGQA transfer（70 题，duration 0.682 强项 + open/sequencing 弱项如实）。
- 5.8 Annotation audit（n=30，97%）+ **Threats to validity**：qwen judge 自偏好（gpt-4 重评预案）、子集规模、单 benchmark —— 集中一节坦白，好过散落各处被挑。
- 5.9 Case study（1-2 个真实 trace：search→confidence 不足→explore→带溯源作答；从 benchmark_mmbv_final.json 里挑）。

### Ch.6 Conclusion & Future Work（~5%）
结论按三个 RQ 收口；future work 直接用 roadmap：第二基准复现（EgoSchema/Video-MME long）、gpt-4 judge、embedding 检索（附架构调研的"为什么现在不动"论证）、多轮指代/时序定位亮点实验、小时级外推。

### Appendices
A. 三套系统 prompt 全文（v1 / v2 core / noexplore）；B. 复现指令（build 子集 + run_benchmark 命令）+ 开源仓库链接；C. 工程规范（CLAUDE.md 的 fail-loud/mock 契约——AI 辅助开发的方法论沉淀，答辩时的差异点）；D. 补充表格（per-dimension 全表、AGQA per-category）。

## 2. 材料映射表（写哪章先开哪份文档）

| 章节 | 直接喂料的仓库文档 |
|---|---|
| Ch.1/摘要 | README.md 三句话、review §Q0/§2.1 |
| Ch.2.4 定位表 | review §2.2（撞车风险表展开成文） |
| Ch.3 | progress.md Phase 12-13、README「为什么是 v2」 |
| Ch.4 | docs/architecture.md、README 核心设计、builder.py/react_agent.py（配图与伪代码） |
| Ch.5 | **benchmark_mmbv_final_analysis.md（唯一取数源）**、benchmark_mmbv_final.json（case study 原始 trace）、benchmark_v2_agqa.md、annotation_audit.json、progress.md §14.1/14.2（负结果） |
| Ch.6 | review §5 roadmap、architecture_review_202607.md |

## 3. 写作顺序（按依赖关系，不按章节号）

1. **先画图后动笔**：把全文 6-8 张图先做出来——架构图、时长桶折线（money chart）、归因柱状、维度对比、frames-touched、case study trace 图。图定了，Ch.4/5 的文字就是给图配说明。
2. **Ch.5 先写**（数据全在、表格现成，最不需要灵感）→ **Ch.4**（对着代码写，最熟）→ **Ch.3**（progress.md 改写）→ **Ch.2**（读文献最耗时，穿插做）→ **Ch.1 与 Abstract 最后写**（等你知道全文到底证明了什么）。
3. 每写完一章给导师/postdoc 过一轮，不要憋大招到最后。
4. gpt-4 重评若在提交前完成，全文数字换一版（脚本零成本）；来不及则维持 qwen-max + threats to validity 披露，答辩口径已在 review Q6 备好。

## 4. 避坑（与 review 面试纪律同源）

- **主张纪律**：全文统一「evidence localization & integration」口径；「temporal structuring」只作机制描述，绝不写 "improves temporal reasoning"（TR 是输的维度）。
- **不可比性主动声明**：150 题自采样子集 ≠ 公开榜，Ch.5.1 白纸黑字写清，别让委员先发现。
- **不写已撤回的结论**：任何 token/成本节省表述禁用；成本如实写 2.1×，卖点是帧效率与长视频精度。
- **负结果是资产**：14.1/14.2 写进 5.6 时用"归因剩余差距"的框架，语气是 systematic elimination，不是 things that didn't work。
- 数字只从 §1.4 / final_analysis 取，写完用 grep 对一遍全文数字与来源。

## 5. 需要你先确认的三件事

1. EEE 学院 dissertation 的**页数/字数、模板、提交时间点**（决定各章配重与倒排日程）。
2. 导师/postdoc 对**Ch.3 保留多少**的偏好（有的导师喜欢演进叙事，有的要求方法先行——本框架默认保留，因为它是你区别于"调包做了个 agent"的核心证据）。
3. 是否要求先发表/投稿后才答辩（决定 workshop 投稿与论文写作的先后）。
