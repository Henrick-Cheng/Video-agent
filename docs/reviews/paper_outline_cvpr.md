# 会议论文大纲(CVPR 2026 模板)—— 与学位论文大纲的分工

> 定位:本文档是**会议版**(8 页正文 + supplementary)的全文规划,是 `thesis_outline.md`
> (学位版 6 章大纲)的姊妹篇。会议论文不是"更短的学位论文":贡献驱动、密度高、
> Related Work 定位、次要内容分流到 supplementary。凡与学位版共享的红线
> (口径、主张纪律、诚实性)一律沿用,不再重复论证。
>
> 落地文件:`docs/thesis/latex/conference/`(CVPR 2026 模板,Overleaf)。
> 当前已有 sec/method.tex(§3)与 sec/experiments.tex(§4);其余节照本大纲后续补。

## 0. 标题与一句话主张

- 标题沿用学位版推荐:*Scene Graphs as Evidence Indexes: Lazy Memory and
  Confidence-Driven LLM Agents for Long-Video Question Answering*。
- 一句话主张(全文统一口径,与 review §Q0 一致):**long-video multimodal evidence
  localization & integration** —— 场景图是证据的时序索引而非答案来源;绝不写
  "improves temporal reasoning"(TR 是输的维度)。

## 1. 贡献列表(会议口径,Intro 末尾的 bullet;不沿用学位版 RQ1–RQ3 叙述形式)

1. **提出把场景图当"证据目录"而非"答案来源"的长视频 QA 记忆设计**:lazy 三层记忆
   (L0 全局 / L1 密集 caption 证据 / L2 时序三元组索引)+ provenance pull-back 机制,
   结构化事实只负责定位,原始 caption/旁白才是证据载体。
2. **置信度驱动的感知预算编排**:agent 自评 1–3 置信度决定是否追加感知调用,平均每题仅
   3.6 帧(固定基线 8 帧)即反超;跨题持久记忆使后续问题常零感知成本命中。
3. **严格的公平归因协议**:同帧数+旁白的 vlm_transcript 公平基线把增益干净拆成模态
   (+0.249)与架构(+0.257;gpt-4-turbo 口径 0.265)两半;双 judge 交叉验证
   (差 <0.015)证伪判分自偏好。
4. **成本-精度前沿的实测回应**:dense 均匀采样加密到 16/32 帧仍不追平,log-线性外推需
   22×–108× 帧预算才达 agent 3.6 帧的水平——"为什么不直接喂整个视频"从推测变实测。

## 2. 章节骨架与素材映射

| 会议版节 | 内容 | 素材来源(学位版/仓库) | 页预算(约) |
|---|---|---|---|
| Abstract | 主张一句 + 机制一句 + 主结果两句(1.98 vs 1.71/1.49;3.6 帧;HL ~2.9×;22×–108×) | README "In three sentences" + review §1.4 | 0.3 |
| 1 Introduction | 长视频 QA 感知预算问题 → **v1 诊断压缩为动机段**(triplet 有损瓶颈 + 预建不摊销,数字只留 v1 1.193 一处)→ 三设计需求一句带过 → 贡献列表(§1) | 学位版 Ch.1+Ch.3 折叠;progress.md Phase 12-13 | 1 |
| 2 Related Work | ①长视频 QA 与 dense-frame VLM;②video scene graphs(答案源 vs 索引的对比定位);③LLM agents / tool use(ReAct 一脉);④benchmark 与 LLM-judge | review §2.2 定位表;学位版 Ch.2 压缩 | 0.75 |
| 3 Method | 现有 `sec/method.tex`(Ch.4 逐字转换版)。**后续可做一轮"会议化紧缩"**(4.5 实现细节剪短、Table 4.3 常数表移 supplementary),本轮不动 | 学位版 Ch.4 | 2.5–3 |
| 4 Experiments | 见 §3(本大纲) | 学位版 Ch.5 压缩 + supplementary 分流 | 2.5 |
| 5 Conclusion | 三条贡献收口 + limitation 一句(单 benchmark、子集)+ future(第二基准复现) | 学位版 Ch.6 压缩 | 0.3 |
| References | 现有 refs.bib + 评测新增(MMBench-Video/AGQA/GPT-4 等) | — | 不计页 |

**砍弃清单**(学位版有、会议版正文不设):Ch.3 独立成章(→ Intro 动机段 + 主表 v1 行)、
RQ1–RQ3 章节化叙述(→ 贡献列表)、AGQA 独立小节(→ Limitations 短段)、标注审计独立小节
(→ Limitations 短段)、case study 独立小节(→ Analysis 内一段 qualitative example)、
Table 4.3 全量常数表(→ supplementary,本轮暂留正文)。

## 3. §4 Experiments 结构(本轮落地)

- **4.1 Setup**:150 题分层子集(seed=42,TR/HL 超采,**白纸黑字声明不可与公开榜直接比**;
  重加权构成偏差 ≤0.04)、VLMEvalKit 0–3 判分协议复刻、双 judge(gpt-4-turbo 论文口径 /
  qwen-max 稳健性对照,差 <0.015、逐题一致率 0.76–0.81)、runs=3、真实 usage 计量、基线
  (vlm_direct@8 / vlm_transcript@8 公平基线 / v1)。
- **4.2 Main Results & Attribution**:主表(两 judge 总分 ±std、Frames/Q、Tokens/Q、v1 行);
  抗噪判据 gap 0.257 > std 和 0.121;归因阶梯正文一段(+0.249 模态 / +0.257 架构,gpt 0.265)。
- **4.3 Analysis**:维度全表(table*,Table-3 版式,gpt-4-turbo)+ 时长桶小表(qwen 派生,
  注明);叙述:Perception 大胜(2.04 vs 1.42)/ HL 卖点(2.29 vs 0.78,~2.9×)/
  Reasoning 近平(同一 LLM)/ **TR 输如实披露**(1.74 vs 1.87,模态驱动);舒适区 ≈90s;
  qualitative example 一段(真实 trace:Search→置信度不足→Explore→带溯源作答)。
- **4.4 Frame Scaling**:图(frame_scaling.svg)+ common-147 表;vlm_direct 32f 仍差
  0.23–0.43,外推 22×–108×;vlm_transcript 仅宽松 judge+32f 入噪声带(gap 0.025,严 judge
  差 0.29);内容审核误杀披露(8f=0→16f=1→32f=3,确定性)脚注;全 150 口径脚注一句
  (supplementary 全表)。
- **4.5 Negative Results & Limitations**:oracle routing 证伪(1.933→1.733,选择偏差)、
  证据加密证伪(0/4,能力天花板)——框架是"剩余差距的系统性归因";AGQA 迁移 2–3 句
  (70q runs=1:judge 0.436,duration 0.682 强,open 0.190/sequencing 0.286 弱,
  详表 see supplementary);标注审计 2–3 句(n=30,97% supported,天花板 ~0.98,PROXY
  披露,详情 see supplementary);limitations:单 benchmark、子集规模、成本如实 2.1×
  (卖点是帧效率与长视频精度,非省钱)、滚动模型别名。

## 4. Supplementary material 分流清单(投稿时单独打包,本轮不产出)

1. AGQA 70 题全表(judge + EM 双口径、分类别、per-video)+ EM-vs-agent 方法论注记
   (false-positive 实例 03PRW)。
2. 标注审计细节(n=30 抽样协议、supported/partial/unsupported 分布、PROXY 局限、0434 锚例)。
3. Case study 完整 trace(工具序列、时间戳、证据链原文;正文只留压缩段)。
4. Frame-scaling 全 150 口径表(含审核 0 分;注明其低估 dense 基线)+ 16f/32f 维度全表。
5. L2 维度全表(±std,gpt-4-turbo 与 qwen-max 双口径)+ 26-leaf 表。
6. 三份 system prompt(v1 / v2 core / noexplore)与复现命令(对应学位版附录 A/B)。
7. Method 溢出件(后续紧缩时移入):Table 4.3 常数表全量、Algorithm 4.1 扩注。

## 5. 图表配额(正文)

| # | 类型 | 内容 | 状态 |
|---|---|---|---|
| Fig. 1 | 图 | 系统架构(ch4_architecture.svg) | 已有 |
| Fig. 2 | 图 | frame-scaling 曲线(frame_scaling.svg,双 judge 两栏) | 已有,复用 |
| Tab. 1 | 表 | 三层记忆概览(method) | 已有 |
| Tab. 2 | 表 | 工具契约(method,table*) | 已有 |
| Tab. 3 | 表 | 常数表(method;后续紧缩候选移 supplementary) | 已有 |
| Tab. 4 | 表 | 主结果(两 judge ±std + frames + tokens + v1) | 本轮新增 |
| Tab. 5 | 表 | 维度全表 Table-3 版式(table*) | 本轮新增 |
| Tab. 6 | 表 | 时长桶 | 本轮新增 |
| Tab. 7 | 表 | frame-scaling common-147 | 本轮新增 |

(时长桶折线 "money chart" 与归因柱状图:学位版规划的图,会议版先用表格承载,后续如需
可再补——与用户已确认的"现成图+表格先行"策略一致。)

## 6. 写作红线(沿用学位版大纲 §4,凡此处未列的以彼处为准)

- 判分口径逐句标注:论文级/维度级 = gpt-4-turbo;抗噪 ±std = qwen runs=3;时长桶/归因
  派生 = qwen 原始分(文中注明)。
- 帧数写 **3.6**(runs=3 权威);81/69 分布标 runs=1 诊断口径。
- 预算表述用 instructed / enforced 二分(≤2/轮、≤3 轮是 prompt 指令;唯一硬上限
  recursion_limit Λ=40)。
- 成本如实 2.1×;禁一切省钱表述;不可比性主动声明;负结果写成归因而非失败流水账。
- 数字只从 review §1.4 / final_analysis / gpt4judge 报告取;写完 grep 对源。
