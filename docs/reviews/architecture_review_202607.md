# 架构调研：记忆 / 工具 / 编排的优化空间（2026-07）

> 范围：逐行审读 `react_agent.py` / `session.py` / `memory_search.py` / `segment_inspector.py` / `retriever.py` / `main.py` / `keyframe.py` 帧落盘 / `config.py`。
> 分类原则：**行为中立**（不改变 agent 决策与输出，随时可做）vs **行为改变**（会使代码与已收官的 mmbv runs=3 数字脱钩，必须重跑评测才能声称，列入 roadmap 不现在做）。

## 一、行为中立 — 本轮已落地

| 发现 | 问题 | 处置（本轮） |
|---|---|---|
| **VideoSession 无锁** | 纯 dict/list 状态，工具直接读写；CLI 单线程安全，服务端并发同 session 提问会竞态 | API 层 per-session `threading.Lock`（ask 期间持有），不同 session 并行不受影响（`src/api/app.py`） |
| **帧文件泄漏** | 帧写到 `tempdir/video_agent/<session_id>`（`keyframe._frame_dir`），无任何清理路径 | API `DELETE /sessions/{id}` 时 `rmtree`；CLI 短生命周期影响小，暂不加 |
| **运行时辅助只在 main.py** | 递归预算推导 + pseudo-call 纠正重试是产品语义的一部分，却住在入口脚本里，API 无法健康复用 | 提升为 `react_agent.get_recursion_limit` / `invoke_with_retry(on_retry=…)`，main.py 薄委托（触发条件/话术/公式逐字不变） |

## 二、行为中立 — 待做（P2，有空再做）

1. **prompt 模块化**：三套系统 prompt（v1 / v2 core / v2 noexplore，各 50–100 行）内嵌在 `react_agent.py`，无版本管理、A/B 需改源码。抽到 `src/agents/prompts.py` 即可；抽取时逐字节保持不变（prompt 是 benchmark 行为的一部分）。
2. **session 序列化**：`VideoSession`（scene_graph + segments + transcript）可 JSON 化 → 服务重启不丢会话、同视频跨会话复用 L0/L1。API 已有清晰边界，加 `to_dict/from_dict` 即可。
3. **transcript 分词缓存**：`search_memory` 每次调用对全部转写行重跑 `tokenize`（含词形还原）。当前规模（≤600s 视频）无感；小时级视频前先在 session 上缓存 `[(row, token_set)]`。
4. **帧提取 decord→cv2 回退逻辑重复**：`keyframe._open_video` 与 `frame_inspector._extract_single_frame` 各一份；合并为共享 helper。低收益，排最后。

## 三、行为改变 — 不做，进 roadmap（动了就要重跑 benchmark）

| 方向 | 依据 | 为什么现在不动 |
|---|---|---|
| **embedding/FAISS 检索**（L2 三元组 + L1 caption + L0 转写） | 14.1 失败分桶：3/10 失败源于 token-overlap 漏检转写命中（同义词盲区）；`retriever._score_text` 是纯词重叠 | 最有希望的单项升级，但会改变 search_memory 命中 → 改变探索决策 → 全部数字失效；应作为第二基准评测时的对照实验一起跑 |
| **置信度判据细化** | 已知局限：「图里有相关但不充分证据」会提前直答（README 局限第 4 条） | 同上；且 14.1 证明 oracle 路由都不涨分，收益上限存疑 |
| **explore 窗口帧数自适应**（>6 帧） | — | **明确不做**：14.2 取证深度实验已证伪（0/4），残差是 VLM 能力天花板 |
| **时间约束检索泛化**（`_extract_time_constraint` 只认 begin/end/数字） | 中段表述（"halfway"、"middle"）不触发时间过滤 | 影响面窄；若做 embedding 升级则顺带覆盖 |

## 四、结论

v2 核心链路（三层记忆 → 联合检索 → 置信度编排）的实现与设计文档一致、无腐坏；本轮的真实短板都在**服务化边界**（并发、清理、逻辑复用），已随 FastAPI 落地一并修掉。剩余优化里唯一值得投入的是 embedding 检索，但它属于「第二基准评测周期」的实验项，不属于工程整备项——在那之前动它只会让代码失去与权威数字的对应关系。
