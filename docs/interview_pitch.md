# Video Agent 面试叙事手册

> 不是项目文档,是**自己面试前过一遍用的稿子**。
> 关键数字、关键故事、可能的追问都在这一份里。

---

## 电梯版(30 秒,开场)

> "我做了一个**基于 ReAct Agent + 时序场景图的中文视频问答系统**——把视频从『连续帧序列』转写成『⟨主体, 关系, 客体, t_start, t_end⟩ 的结构化记忆』,让 Agent 用 4 个工具按需调度。在两个数据集上做了诚实的横评:**公开 AGQA Charades 上 Agent 反超 vlm_direct 基线(0.364 vs 0.326),且 token 开销仅其 1/4**;自建 cooking.mp4 上 vlm_direct 更强——两个数据集呈现 Pareto 互补。整套系统感知 / 记忆 / 推理 / 评测端到端自建,benchmark 自己跑了两次大型返修,所有结果诚实写进了 progress.md。"

---

## STAR

### S — Situation(背景)

视频 QA 的两条主流路线各有硬伤:

| 路线 | 问题 |
|------|------|
| **VLM 直接看帧**(GPT-4V / Qwen-VL) | 长视频 token 爆炸;追问无记忆复用;固定帧采样在长视频上覆盖率塌缩 |
| **纯 RAG**(先生成描述入库 → 检索回答) | 描述粒度死板;无法做"何时—何地—谁对谁"的时序关系推理 |

更关键的:**两种方法都没有"我想再看一眼第 95 秒"的主动权**——视觉信息一次性吃进去,模型只能用一次。

### T — Task(目标)

1. **结构化中间表示**:把视频抽象成可查询、可累积、可精化的**时序场景图**,而不是把所有帧塞给 VLM
2. **Agent 按需调度**:让 LLM 自己决定先抽帧、先查图、还是回头看某一帧
3. **可信评测**:自建 benchmark + 接公开数据集,用 LLM-as-Judge 做 3 方案横评,把结论写实

### A — Action(实现,4 个技术决策)

#### ① 架构:ReAct Agent + 时序场景图 + 4 个原子工具

```
extract_keyframes  →  build_scene_graph  →  query_scene_graph
                              ↑                      ↓
                              └──── inspect_frame ───┘   ← 渐进式精化回写
```

- LangChain 1.x `create_agent`,不手写 router——让模型自己读 ReAct 系统提示推理下一步
- `VideoSession` 闭包注入的共享可变状态,4 个工具同享一份 cached_frames + scene_graph
- 双后端开关:**DashScope**(qwen-vl-plus + qwen-plus)/ **本地 vLLM**(Qwen3-8B + Qwen2.5-VL-7B-AWQ,单卡 4090 共存)

#### ② 场景图构建:3 道去重 + 50 词关系闭词表

VLM 输出天然不稳定(同一个人在 batch1 叫"红衣男子"、batch2 叫"穿红外套的人")。**三道防线叠加**:

| 防线 | 机制 | 何时生效 |
|------|------|----------|
| ① 预防 | Prompt 注入已知实体列表 | VLM 调用前 |
| ② 修复 | `difflib.SequenceMatcher ≥ 0.85` + 同 type | 跨 batch 后处理 |
| ③ 兜底 | 字符串字面相等 | 写入 SceneGraph 时 |

外加 **50 词关系词表强约束**(8 类),让 VLM 不能自造关系动词——下游 retriever 的关键词匹配才有意义。

#### ③ 性能:ThreadPoolExecutor 并发 + 三层 JSON 兜底

- 16 帧拆 4 个 batch,**ThreadPoolExecutor 并发 3 路**,把 60–90s 的串行 VLM 调用压到 20–35s
- VLM 输出 JSON 三层兜底:`json.loads` → 首尾 `{...}` 抽取 → **括号深度匹配单独抠 entities/relations 数组**(应对 Qwen-VL 已知幻觉模式:外层 `}` 永不关闭)

#### ④ 评测:多视频 LLM-as-Judge,两个数据集横评

- **自建** cooking.mp4(25 题 / 5 类)+ **公开 AGQA Charades**(10 视频 / 70 题 / 自动抽样 + LLM 翻译,3 轮 prompt 迭代修了子句丢失、词义错、Q/A 不一致)
- 评测脚本支持**多视频分组**:每视频建一次图,该视频的题共用——拼接结果让 `_aggregate` 自动按类别聚合
- 3 方案统一接口、**3 run × mean ± std**

### R — Result(诚实数据 + Pareto 故事)

#### 数据 1:公开 AGQA Charades(10 视频 × 70 题 × 3 轮)

| 方法 | 准确率 | Tokens/Q | 时间 |
|------|--------|----------|------|
| **agent** | **0.364 ± 0.015** | **1,368** | 24.4s |
| rag_only | 0.186 ± 0.031 | 838 | 4.0s |
| vlm_direct | 0.326 ± 0.007 | 6,041 | 4.5s |

**Agent 双赢**:准确率 +11.7% 相对、token **便宜 4.4×**。
**分类:** duration **2.1× 领先**(0.318 vs 0.152)、binary 略胜、sequencing 输 0.07、open 持平。

#### 数据 2:自建 cooking.mp4(25 题 × 3 轮,消除字幕作弊后)

| 方法 | 准确率 | Tokens/Q |
|------|--------|----------|
| agent | 0.313 ± 0.019 | 1,383 |
| rag_only | 0.040 ± 0.033 | 1,235 |
| **vlm_direct** | **0.373 ± 0.009** | 6,039 |

vlm_direct 整体领先,但 Agent 在「计数 / 出现」类**唯一明确领先**(0.133 vs 0.000)。

#### 整合结论:Pareto 互补,不是"全胜"

- Agent 赢:**AGQA 整体 / duration / cooking 计数 / token 成本(始终 1/4)**
- vlm_direct 赢:**物体识别 / 实体属性 / AGQA sequencing**
- **核心定位:结构化时间推理 + 跨帧聚合 + token 效率,不在单帧 dense perception**

---

## 项目亮点(面试官会盯着追问的部分)

### 亮点 1:**两次诚实的负结果返修**(最重磅,先说这个)

1. **Phase 10 cooking**:发现自己的 `vlm_direct` 基线**默默耦合了 agent 配置**(从 agent 预建的 frame cache 取帧,`keyframe_count` 8→16 改写了基线输入)。主动审计、修复、**vlm_direct 反而从 0.293 涨到 0.373**——也就是**我自己的对照变更强了**,推翻了早期"agent 关系推理 2.7×"的假胜论。完整记录写进 progress.md 第十阶段。

2. **Phase 11 AGQA**:跑 AGQA 前我预测「Charades 短视频 → 场景图稀疏 → agent 会输」。**实测打脸——agent 反胜**(0.364 vs 0.326),原因是 AGQA 的 duration 类直接对接三元组时间窗。整个反转故事写进 progress.md 第十一阶段的「与睡前预测的诚实复盘」段落。

> 这两次返修是这个项目**最值钱的部分**——证明我**知道什么是 confound、什么是诚实工程**。

### 亮点 2:**两个工具的非对称设计**(build_scene_graph vs inspect_frame)

| 维度 | build_scene_graph | inspect_frame |
|------|-------------------|---------------|
| 调用模式 | 多图单次 + ThreadPoolExecutor 3 路并发 | 单图单次 |
| 输出 schema | 严格 JSON + 50 词关系闭词表 | 自由问答 + 简单 JSON |
| `source` 标签 | `"vlm"` | `"inspector"` |
| 用途 | 冷启动主干(一次性、慢、严格) | 温启动补丁(精确点位、快、宽松) |

**若问"为啥不合并":** 合并 = 强迫 Agent 在"全量重建"和"单点补充"之间二选一,丢掉了正交性。Agent 的「省 token」靠的就是先粗后精的分级。

### 亮点 3:**渐进式精化的写回闭环**

`inspect_frame` 不只是"看一眼回答"——它把发现的实体和关系**回写到 SceneGraph**:
- 新实体打 `type="object"`、attributes 留空(避免与 build 阶段精细标注冲突)
- 关系单点时间窗(`t_end = ts + merge_window_sec`)
- source 标签 `"inspector"`,便于溯源
- 通过 `session.update_scene_graph` 这个**唯一写入入口**,复用 build 的去重逻辑

下次再 query 时,inspect 找到的信息**已经在图里**——这是 RAG 系统罕见的「记忆累积」能力。

### 亮点 4:**端到端 Real/Mock 降级链**

从 `extract_keyframes`(path 不存在 → mock)→ `build_scene_graph`(无 API key / 无真实 path / mock.enabled → mock)→ 所有下游工具,**任何一环降级,下游自动跟随**。

意义:**离线 CI 能跑通整个 pipeline、无 GPU 机器能演示完整流程**——是工程而不是 demo。

### 亮点 5:**评测框架的两次架构演进**

- v1(Phase 1–7):单视频硬绑定,每轮只建一张图,所有题共用
- v2(Phase 11):多视频分组,按 `video` 字段 group,每视频建一次图复用;`_aggregate` **零改动**,新功能爆炸半径极小

向后兼容做到了:旧 cooking.mp4 单视频 benchmark 行为完全不变。

### 亮点 6:**Token 经济学的可量化论证**

> 用户问 1 道题:vlm 6K token,agent 7K(含建图),agent 反而贵。
> 用户问 10 道题:vlm 60K,agent 16K(建图 + 10×查询),**agent 便宜 3.75×**。
> 用户问 100 道题:vlm 600K,agent 106K,**agent 便宜 5.7×**。
> ——把视觉理解从 O(N×frames) 降到 O(frames + N) 的**根本性差异**。

实测两个数据集都一致显示 agent token 成本 ~1/4 vlm_direct(cooking 1383 vs 6039;AGQA 1368 vs 6041)——一致到几乎和数据集无关,这是结构性的。

---

## 面试官常见追问 + 备答

### Q1: "Agent 在 cooking 上输了,这项目意义何在?"

> 准确率 84% / token 22%,**Pareto 前沿的不同点**。在 1 题场景 vlm 赢;在长会话 / Agent Workflow 场景 agent 赢。而且 **AGQA 上 agent 反超**——证明结构化时间窗在 duration 类有 2.1× 的不可替代性。**没赢全场不等于没有价值,赢的赛道清晰可量化才有价值。**

### Q2: "AGQA 上你为什么会预测错?"

> 因为我基于「视频短 → 图稀疏」的纸面逻辑想当然了,**没考虑 AGQA 问题本身的结构**。AGQA 的题是从场景图生成的,duration / before-after 这类是题面就嵌着时间结构,正好打到我场景图的 t_start/t_end。这次复盘让我学到:**结构性假设要数据验证才算数**——和 Phase 10 那次 vlm_direct 翻盘是同一种诚实。这个反转过程我完整写进 progress.md 了。

### Q3: "scene graph 的 dedup 阈值 0.85 是怎么定的?"

> 经验值。jieba 分词后 SequenceMatcher 比值:0.9 会漏合"红衣男子 / 穿红外套的人",0.8 会误合"锅 / 锅盖"。我做过手动 grid search 但没放进 paper-style ablation,是 future work。**这个阈值是 prompt 注入(预防)+ 写入字面去重(兜底)三道防线中的第二道**,所以鲁棒性不强求。

### Q4: "为什么不直接用 GraphRAG / Microsoft 的方案?"

> GraphRAG 是为文本设计的,节点抽取依赖 LLM 读全文。视频里"全文"是 N 帧图像,必须用 VLM——所以我的 `build_scene_graph` 本质是 GraphRAG 的视觉版,但加了三个视频特有的约束:**时间窗、关系闭词表、跨 batch 命名稳定化**。

### Q5: "ReAct vs router-based agent 怎么选?"

> 我选 ReAct 是因为问题类型多样(AGQA 4 类 / cooking 5 类),写死 router 会丢失泛化。代价是 Agent 偶尔会做次优工具序列——我在 system prompt 里给了 4 步决策模板(先 extract → 再 build → 再 query → 不确定再 inspect),实测 cooking 平均 3.6 次工具调用、AGQA 平均 4.5 次工具调用收敛。

### Q6: "sequencing 类在 AGQA 上输给 vlm 你怎么解释?"

> 诚实承认这是**已知短板**。原因:`merge_window_sec=3.0` 在 30s 短视频上时间精度不够——两个事件相差 4s,场景图里会被合并成时间窗重叠,顺序信息丢失;而 vlm_direct 看 4 帧的时序就能直接读出来。**修法**有两条:① 缩小 merge window 到 1s(代价:同一动作会被拆成多段)② 加一个专门的「事件时间线」工具,按 t_start 排序输出,不做窗口合并。我把这写在 progress.md 的下一步 #1。

### Q7(如果有时间):"如果让你重新做一遍这个项目,哪里会做不一样?"

三件事:
1. **先接公开数据集再做自制 benchmark**——自制单视频是 confound 重灾区,我花了 Phase 1–10 才在 Phase 11 接公开数据集,有点本末倒置
2. **更早做长视频测试**——cooking 202s 已经看不出 amortize 优势,长视频才能彻底证明 Pareto
3. **场景图建图加 ablation**——目前只有 prompt 上的经验调整,没系统对比 batch_size / merge_window / dedup_threshold 对最终 QA 准确率的影响

---

## 一句话收尾

> "这个项目让我把 **多模态感知 / Agent 编排 / 结构化记忆 / benchmark 测量学** 四件事串起来做了一遍——而且我**没有粉饰任何结果**,Phase 10 的 vlm_direct 翻盘和 Phase 11 的 agent 反超**两次返修**全部写进了 progress.md。"

---

## 速查卡(面试前 1 分钟过一遍)

| 关键数字 | 值 |
|---------|-----|
| AGQA agent / vlm | **0.364 vs 0.326**(agent +0.038) |
| cooking agent / vlm | 0.313 vs 0.373(vlm +0.060) |
| Agent token 优势 | **~4.4× 便宜**(1,368 vs 6,041) |
| AGQA duration 类 | **agent 0.318 vs vlm 0.152(2.1×)** |
| cooking 计数 | agent 0.133 vs vlm 0.000(唯一明确赢) |
| AGQA sequencing(承认输) | agent 0.381 vs vlm 0.452 |
| 关系词表 | 50 词,8 类 |
| 去重阈值 | 0.85(SequenceMatcher) |
| 测试覆盖 | 38 passed / 12 skipped |
| 评测规模 | 95 题(70 AGQA + 25 cooking)× 3 run |

| 关键故事 | 一句话 |
|---------|--------|
| **Phase 10 翻盘** | 发现 vlm_direct 抽帧耦合 agent 配置,主动修,我自己的对照变更强了 |
| **Phase 11 反转** | 跑 AGQA 前预测 agent 会输,实测反胜,在 duration 上 2.1× |
| **两次返修** | 都诚实写进 progress.md,这种 commit history 在面试时可以直接展示 |
