# Video Agent — 系统架构详解（v2）

> 2026-07-14 同步至 v2（lazy 三层记忆 + 置信度循环）。v1 架构不再单独成文，
> 其要点收进文末 [v1 → v2 对比表](#v1--v2-架构对比)；v1 代码仍在役
> （benchmark 基线 + `--mock` 离线路径），见 `CLAUDE.md`。

## 总体架构

```
┌───────────────────────────────────────────────────────────────────────┐
│  入口:  CLI main.py (single / interactive)  ·  FastAPI src/api/app.py  │
│         (会话注册表 / per-session 锁 / SSE 流式 trace / mock 会话)      │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ prepare_l0(session)   ← 每视频一次、幂等
                                │ build_l0_context() + question
┌───────────────────────────────▼───────────────────────────────────────┐
│         v2 Agent (LangChain create_agent / LangGraph + qwen-plus)      │
│                                                                        │
│  置信度驱动循环:                                                        │
│    search_memory (必先调用, 免费)  →  自评置信度 1–3                    │
│      < 3 → explore_segment (每轮 ≤2 次, 共 ≤3 轮) / inspect_frame      │
│      = 3 或预算耗尽 → 作答 (缺席≠否定; 证据不足须声明而非猜测)          │
│                                                                        │
│  防护: pseudo-call 检测 + 纠正性重问;  recursion_limit = iters×5+10    │
└──────┬─────────────────────────┬──────────────────────┬────────────────┘
       ▼                         ▼                      ▼
┌───────────────┐      ┌──────────────────┐    ┌─────────────────┐
│ search_memory │      │ explore_segment  │    │ inspect_frame   │
│ 三层联合检索  │      │ 细看一个时间窗   │    │ 单帧像素级精读  │
│ 零 API 成本   │      │ ≤6 帧 1 次VL调用 │    │ (读文字/计数)   │
│               │      │ 写 L1 + L2       │    │ 发现写回 L2     │
└───────┬───────┘      └────────┬─────────┘    └────────┬────────┘
        │                       │                       │
┌───────▼───────────────────────▼───────────────────────▼───────────────┐
│                  VideoSession — 三层 Lazy 记忆 (src/memory/session.py) │
│                                                                        │
│  L0 全局层(每视频一次):  global_summary (8 帧摘要, 1 次 VL 调用)        │
│                         transcript (本地 ASR 全量转写)                 │
│                         duration_sec · explored_windows                │
│  L1 证据层(按需生长):    segments {seg_id → 时间窗 + 密集 caption}      │
│  L2 索引层(按需生长):    SceneGraph 三元组 ⟨s, r, o, t_start, t_end⟩   │
│                         source="seg:<id>" — 每条三元组可溯源到 L1     │
│  cached_frames · query_history                                        │
└───────────────────────────────┬───────────────────────────────────────┘
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 感知层:  VLClient (DashScope | vLLM 双后端, 三级 JSON 容错, 自动缩放)   │
│          faster-whisper 本地 ASR (转写落盘缓存, 跨 run 复用)            │
│          UsageLedger 线程安全真实计费账本 (全部 token 来自 API usage)   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 单题生命周期

```
① prepare_l0(session)          每视频一次, 幂等 (react_agent.py)
     8 帧均匀采样 → 1 次 VL 调用生成全局摘要 (失败则优雅降级为空摘要)
     faster-whisper 本地转写 → session.transcript (磁盘缓存)
② build_l0_context(session)    渲染 L0 前缀:
     [Video] 时长 + [Global summary] + [Narration transcript 全文]
     + [Explored windows] (跨问累积)
③ agent.invoke(L0 前缀 + 问题)  置信度循环 (见上图)
④ invoke_with_retry            若最终消息形如 `tool(...)` 纯文本
     (pseudo-call), 追加纠正指令重问一次
```

关键点：**L0 是替代 v1 全量预建的轻量前置成本**（1 次 VL 调用 + 本地 ASR）；
其余一切按需——建图本身是 agent 的逐题运行时决策，不是预处理步骤。
MMBench-Video 150 题中 81 题止步于 ①②+免费检索直答，69 题自主升级探索，
平均每题仅访问 3.1 帧。

---

## 关键组件说明

### 1. v2 Agent 工厂 (`src/agents/react_agent.py::build_agent_v2`)

- 基于 LangChain 1.x `create_agent`（内部 LangGraph），LLM 为
  `qwen-plus-latest`（DashScope）或本地 vLLM。
- 系统 prompt（`_V2_SYSTEM_CORE`）内嵌：置信度流程、窗口策略（短视频先探
  全片；时长比较须覆盖活动完整区间）、grounding 规则（禁用先验知识；转写
  对 why/how/顺序类问题权威；**缺席≠否定**——记忆只覆盖已探索窗口，答
  "no" 前必须先探索验证）。
- `short_answer` 开关切换简短/带时间戳两种答案格式（benchmark 用前者，
  交互产品用后者）；`explore=False` 变体仅保留 search_memory（路由实验
  遗留，产品线不用）。
- 共享运行时防护（与 benchmark 同一实现）：`looks_like_pseudo_call` +
  `invoke_with_retry`（模型把工具调用写成纯文本时纠正重问一次）；
  `get_recursion_limit`（v2 = iters×5+10，由循环形状推导而非拍脑袋）。

### 2. 三个工具 (`src/tools/`)

| 工具 | 作用 | 成本 | 何时调用 |
|------|------|------|---------|
| `search_memory` | 三层联合检索（L2 三元组 + L1 caption + L0 转写行） | 零 API 成本 | **必须首先调用**；每次获得新证据后可再查 |
| `explore_segment` | 细看自选时间窗：窗内均匀 ≤6 帧、1 次多图 VL 调用 → 写 L1 密集 caption + L2 三元组 | 1 次 VL 调用 | 置信度 <3 时，由转写时间戳/摘要/已有命中引导选窗 |
| `inspect_frame` | 单帧像素级精读（屏幕文字、精确计数），发现写回 L2 | 1 次 VL 调用 | 需要单帧细节时 |

### 3. 三层 Lazy 记忆 (`src/memory/session.py`)

```
VideoSession
├── L0  global_summary: str          # 8 帧摘要（prepare_l0 一次性）
│       transcript: [{t_start, t_end, text}]   # ASR 全量转写
│       duration_sec / explored_windows()
├── L1  segments: {seg_id → Segment(t_start, t_end, caption, question)}
└── L2  scene_graph: SceneGraph
        ├── entities: {name → Entity(type, attrs, first_seen, last_seen)}
        └── triplets: [⟨subj, rel, obj, t_start, t_end, conf, source⟩]
                                        source = "seg:<segment_id>"  ← 溯源
```

**设计要点：图 = 证据的时序索引，不是答案来源。** 三元组带
`source="seg:<id>"` 溯源，检索命中三元组会自动回带其父 segment 的完整
caption（provenance pull）——结构化用于定位，原文用于作答，消除 v1
"纯三元组即答案"的有损压缩（v1 教训：纯三元组 RAG 只保住直接看帧约一半
信号）。层数由"检索必须能溯源到证据"反推：去 L2 = 线性扫 caption 丢
时间戳定位；去 L1 = 回到有损三元组。

### 4. 统一检索 (`src/scene_graph/retriever.py::search_memory`)

英文管线（英文迁移后）：nltk WordNet 词形还原（离线降级为后缀 stemmer）
+ 多策略加权匹配。

- **L2 三元组**：实体名精确匹配 / 关系词表匹配 / 多 token 子串累积得分
  / 时间约束过滤（"beginning" / "last" 等）；top-5。
- **L1 caption**：token-overlap 评分 top-3；三元组命中的父 segment 以
  1.0 分强制回带（溯源优先于文本相似度）。
- **L0 转写行**：token-overlap 评分 top-4。
- 返回 `{triplets, segments, transcript_hits, entity_summary,
  explored_windows, found}`——agent 一次调用同时看到结构化事实与其原始
  上下文。

### 5. 建图管线 (`src/scene_graph/builder.py::build_segment`)

explore_segment 的后端，单次 VL 调用同时产出密集 caption 与三元组：

- **实体命名三道防线**：prompt 注入已有实体名（生成端预防）→ 批内去重
  → 跨批与既有图谱对齐（`difflib` 相似度合并）；
- 相邻三元组按时间窗合并（默认 3s）防索引膨胀；
- 三级 JSON 容错解析（直接 parse → 首个 `{}` 提取 → 数组级抢救），
  caption 丢失时从 JSON 前导自由文本抢救。

### 6. 感知层 (`src/perception/`)

- **VLClient**（`vl_client.py`）：OpenAI SDK 兼容封装，DashScope / 本地
  vLLM 双后端一键切换；图像自动缩放；`call_multi` 多图单调用；
  max_retries=6 + timeout=90s（runs=3 共 1350 题 0 error 的可靠性来源）。
- **ASR**（`asr.py`）：faster-whisper 本地转写，结果落盘缓存跨 run 复用。
- **UsageLedger**（`usage.py`）：线程安全计费账本，全部 token 来自 API
  返回的真实 usage；VL / LLM 两条计价线分开，marker 快照逐题归账。

### 7. fail-loud 与 mock 契约（工程纪律，详见 `CLAUDE.md`）

- 真实路径后端不可用 → 工具返回 `{"_mode": "error", ...}`，**绝不静默
  编造证据**（`scene_graph_builder._fail_loud` 等）。
- mock 仅显式开启（`--mock` / API `{"mock": true}`），走 v1 脚本化离线
  agent：真实驱动工具循环，最终输出带 `[MOCK]` 前缀、不虚构任何视频内容，
  由 guard 测试锁死。v2 尚无独立 mock。

---

## 服务形态

| 形态 | 入口 | 说明 |
|------|------|------|
| CLI 单题 / 交互 | `main.py` | 真实后端走 v2（prepare_l0 + 置信度循环）；交互模式跨问复用 L0 与已探索窗口 |
| HTTP API | `src/api/app.py`（FastAPI） | 会话注册表 + per-session 锁（VideoSession 非线程安全）；`POST /sessions` 建会话即跑 prepare_l0；`/ask` 与 SSE 流式 `/ask/stream`；`DELETE` 清理帧目录 |
| 容器 | `Dockerfile` | 瘦身镜像（requirements-serve.txt，无 torch/vllm/ASR 重依赖），mock 模式无 key 可跑 |

---

## 部署架构

```
GPU 机器（单卡 RTX 4090, 24GB VRAM）— 接口就绪, 未实跑（无 GPU, README 已标注）
├── vLLM server (port 8000) → Qwen3-8B (Agent LLM)
└── vLLM server (port 8001) → Qwen2.5-VL-7B-AWQ (VLM)

CPU 机器（开发 / macOS）
└── DashScope API (qwen-plus-latest + qwen-vl-plus-latest)

配置切换：BACKEND=vllm | BACKEND=dashscope
```

## 配置系统 (`src/config.py`)

优先级（高 → 低）：环境变量 → `.env` 文件 → `configs/default.yaml`
（pydantic-settings，嵌套键用 `__` 分隔，如 `MODELS__VL__MODEL_NAME=...`）。

---

## v1 → v2 架构对比

| 维度 | v1 `build_agent` | v2 `build_agent_v2` |
|------|------------------|---------------------|
| **建图时机** | 预处理全量：首题先对全片关键帧批量建图 | 逐题按需：explore_segment 是运行时决策，81/150 题零建图直答 |
| **记忆结构** | 单层 SceneGraph | 三层：L0 摘要+ASR / L1 段落 caption / L2 溯源三元组索引 |
| **图的角色** | 答案来源（三元组即作答依据） | 证据索引（命中回带原始 caption + 旁白，`source="seg:<id>"` 溯源） |
| **模态** | 纯视觉 | 视觉 + ASR 旁白（转写全量入 L0 前缀） |
| **工具集** | extract_keyframes / build_scene_graph / query_scene_graph / inspect_frame | search_memory / explore_segment / inspect_frame |
| **循环控制** | 线性 ReAct（prompt 规定调用顺序） | 置信度自评 1–3 + 硬预算（每轮 ≤2 次探索、共 ≤3 轮） |
| **上下文前缀** | 无（依赖工具输出累积） | L0 前缀：摘要 + 全量转写 + 已探索窗口 |
| **检索** | query_scene_graph（纯三元组，中文 jieba 时期设计） | search_memory（三层联合、英文词形还原、溯源回带） |
| **幻觉约束** | prompt 要求引用证据 | "缺席≠否定"写进编排 + grounding 规则（HL 维度 2.3× 基线） |
| **recursion_limit** | iters×3+1 | iters×5+10（置信度循环形状推导） |
| **每题帧预算** | 全片关键帧建图（无预算概念） | 平均 3.1 帧/题（基线固定 8 帧，−61%） |
| **MMBV 150q runs=3** | 1.193 | **1.984±0.101**（> vlm_transcript 1.727 > vlm_direct 1.478） |
| **现役角色** | benchmark 基线（`agent`）+ `--mock` 离线路径 | 产品主线：CLI / FastAPI / benchmark（`agent_v2`） |

> v1→v2 的两个诊断结论（详见 `progress.md` / `project_review_202607.md`
> §2.1）：①三元组是有损压缩，VLM 看到的属性/文字/因果在"只输出 JSON
> 三元组"一步丢失；②每视频约 1 题的负载下，全量预建的成本永远摊销不回。

---

## 评测方案对比

| 方案 | 记忆 | Agent | 模态 | MMBV 150q（0–3） |
|------|------|-------|------|------------------|
| vlm_direct | ✗（均匀 8 帧直推） | ✗ | 视觉 | 1.478±0.025 |
| vlm_transcript | ✗（8 帧 + 全量转写） | ✗ | 视觉+ASR | 1.727±0.020 |
| rag_only（v0） | 静态场景图 | ✗ | 视觉 | —（早期基线） |
| agent（v1） | 全量预建图 | ✓ | 视觉 | 1.193 |
| **agent_v2（ours）** | 三层 Lazy | ✓ 置信度循环 | 视觉+ASR | **1.984±0.101** |

vlm_transcript 是**同模态公平基线**：与 agent_v2 同帧数量级、同旁白文字，
只差架构——用于把增益拆解为 ASR 模态 +0.249 与架构 +0.257 两部分
（归因方法论，见 `benchmark_mmbv_final_analysis.md`）。
