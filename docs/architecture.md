# Video Agent — 系统架构详解

## 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户 / Gradio UI                              │
│                   问题 (自然语言)  ←→  答案 + trace                  │
└───────────────────────────┬─────────────────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────────────────┐
│                   ReAct Agent (Qwen3 / qwen-plus-latest)             │
│                                                                      │
│  系统 prompt：决策策略 + 证据引用要求（中英双语）                       │
│                                                                      │
│  ReAct 循环 (LangGraph CompiledStateGraph)：                         │
│    Thought → Action → Observation → Thought → … → Final Answer      │
└──────┬──────────────┬──────────────┬──────────────┬─────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐
│ extract_   │ │ build_     │ │ query_     │ │ inspect_frame  │
│ keyframes  │ │ scene_     │ │ scene_     │ │ (VLM 精读)     │
│            │ │ graph      │ │ graph      │ │                │
│ uniform /  │ │ VLM 批量   │ │ jieba +    │ │ 单帧精细分析   │
│ scene_chg  │ │ 多帧理解   │ │ 多策略匹配 │ │ → 写回图       │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬─────────┘
      │              │              │               │
      └──────────────┴──────────────┴───────────────┘
                             │
              ┌──────────────▼──────────────┐
              │         VideoSession         │
              │  (shared state per session)  │
              │                             │
              │  ┌──────────────────────┐   │
              │  │   SceneGraph         │   │
              │  │  entities: dict      │   │
              │  │  triplets: list      │   │
              │  │  <subj, rel, obj,    │   │
              │  │   t_start, t_end>    │   │
              │  └──────────────────────┘   │
              │                             │
              │  cached_frames: dict        │
              │  query_history: list        │
              └─────────────────────────────┘
```

---

## 关键组件说明

### 1. ReAct Agent (`src/agents/react_agent.py`)

- 基于 LangChain 1.x `create_agent` (内部使用 LangGraph)
- LLM：`qwen-plus-latest`（DashScope）或 `Qwen3-8B`（本地 vLLM）
- 系统 prompt 内嵌中文决策策略，避免浪费 API 调用

### 2. 四个工具 (`src/tools/`)

| 工具 | 作用 | 何时调用 |
|------|------|---------|
| `extract_keyframes` | 提取关键帧缓存到 session | 首次调用，策略：uniform/scene_change |
| `build_scene_graph` | VLM 批量分析帧 → 三元组写入图 | 首次需要视觉信息时 |
| `query_scene_graph` | jieba 多策略检索图 | 优先调用（零成本） |
| `inspect_frame` | VLM 精读单帧 + 写回图 | 图检索失败 / 需要细节时 |

### 3. 场景图 (`src/scene_graph/`)

```
SceneGraph
├── entities: {name → Entity(type, attrs, first_seen, last_seen)}
└── triplets: [Triplet(subj, rel, obj, t_start, t_end, conf, source)]
```

**时序三元组格式**：`(subject) --[relation]--> (object) @ [t_start, t_end]`

**去重策略**：
1. VLM prompt 注入已知实体（防止跨批次命名不一致）
2. `difflib.SequenceMatcher` 后处理合并（相似度 ≥ 0.85）

### 4. 中文检索 (`src/scene_graph/retriever.py`)

四层策略（命中率 80%+）：
1. jieba 分词 + 动态用户词典（实体名注入）
2. 精确实体名匹配（权重 +2.0）
3. 关系动词匹配（50 个中文关系词，权重 +1.5）
4. 子串 / 多关键词累积得分（权重 +0.5）
5. 时间约束过滤（"开头"/"最后" 关键词）

### 5. VL Client (`src/perception/vl_client.py`)

- OpenAI SDK 兼容封装，支持 DashScope 和本地 vLLM 两个 backend
- 自动 resize 图像到 `image_max_size`（默认 1280px）
- `call_multi()`：多图单次调用，尝试 JSON mode，失败自动降级
- 三层 JSON 解析兜底（防止 Qwen-VL 输出格式损坏）

---

## 渐进式精化（Progressive Refinement）

```
build_scene_graph(frames)     ← 粗粒度：建图 N1
        ↓
query_scene_graph(question)   ← 快速检索（零成本）
        ↓ miss
inspect_frame(t, question)    ← 精读单帧
        ↓
nodes_added_to_graph: k > 0   ← 发现写回
        ↓
query_scene_graph(question)   ← 再次检索，图已更新到 N2 > N1
```

**关键性质**：`inspect_frame` 的发现自动反向写入 `VideoSession.scene_graph`，
所有后续 `query_scene_graph` 都能查到新内容，形成图-像双向迭代。

---

## 部署架构（生产）

```
GPU 机器（单卡 RTX 4090, 24GB VRAM）
├── vLLM server (port 8000) → Qwen3-8B (Agent LLM)
└── vLLM server (port 8001) → Qwen2.5-VL-7B-AWQ (VLM)

CPU 机器（开发 / macOS）
└── DashScope API (qwen-plus-latest + qwen-vl-plus-latest)

配置切换：BACKEND=vllm (生产) | BACKEND=dashscope (开发)
```

---

## 配置系统 (`src/config.py`)

优先级（高 → 低）：环境变量 → `.env` 文件 → `configs/default.yaml`

嵌套键用 `__` 分隔（如 `MODELS__VL__MODEL_NAME=qwen-vl-max-latest`）。

---

## 评测方案对比

| 方案 | 场景图 | Agent | 自适应采样 | 反向写入 |
|------|--------|-------|-----------|---------|
| vlm_direct | ✗ | ✗ | ✗ | ✗ |
| rag_only | ✓（静态） | ✗ | ✗ | ✗ |
| **agent（ours）** | ✓（动态） | ✓ | ✓ | ✓ |
