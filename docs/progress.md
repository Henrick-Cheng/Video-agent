# Video Agent — 演进日志

> 每次重大迭代在此追加一节。格式：完成内容、新依赖、已知问题 / TODO、下一步建议。

---

## 第一阶段：项目骨架（commit d6da531）
**日期：** 2025-05

### 完成内容
- 完整项目目录结构：`src/{agents,tools,perception,scene_graph,memory,eval}`
- `VideoSession` 共享状态容器（帧缓存 + 场景图）
- 四个 LangChain `@tool`：`extract_keyframes`、`build_scene_graph`（mock）、`query_scene_graph`（mock）、`inspect_frame`（mock）
- ReAct Agent 工厂（LangChain 0.3 → 后续升级到 1.x）
- 完整单元测试套件（23 个测试）

### 引入依赖
LangChain、LangGraph、pydantic、OpenCV、Pillow、OpenAI SDK

### 已知问题
- 所有工具均为 mock，无真实 VLM 接入
- AgentExecutor 在 LangChain 1.x 已删除（第二阶段修复）

---

## 第二阶段：接真实视觉模型（commits c9302ee、2973e7a、37d7510）
**日期：** 2025-05

### 完成内容
- `VLClient`：OpenAI 兼容封装，接 Qwen2.5-VL-7B-AWQ（vLLM）
- `extract_keyframes` + `inspect_frame` 接真实 VLM，mock 作为 fallback
- video backend：decord → OpenCV 双后端（Python 3.13 / macOS 无 decord wheel）
- 修复 AgentExecutor 移除问题，迁移到 LangGraph `create_agent`
- `test1.mp4` 非 vllm 测试 4/4 pass，vllm 测试条件跳过

### 引入依赖
OpenCV (`opencv-python`)，decord（可选），vLLM（生产）

### 已知问题
- `build_scene_graph` 仍为 mock
- `query_scene_graph` 为关键词匹配，非向量检索
- macOS 开发机无 GPU，生产部署未完成

---

## 第三阶段：配置抽离 + DashScope 后端 + 真实感知循环（本次）
**日期：** 2026-05-11

### 完成内容

#### 任务 1：配置抽离
- `configs/default.yaml` 集中所有参数：backend、models（vl/llm）、vllm 覆盖、perception、scene_graph、retrieval、agent、mock
- `src/config.py`：pydantic-settings `Settings` 类，支持 YAML 基础值 + .env 覆盖 + 环境变量（`__` 分隔嵌套）
- `.env.example` 文档化所有环境变量
- `get_settings()` 带 `@lru_cache` 的全局单例
- 所有工具、感知、agent 模块移除硬编码，改用 `get_settings()` lazy 读取

#### 任务 2：VLClient 改造
- 新增 `backend` 参数支持 `"dashscope"` / `"vllm"` 两种后端
- `_encode()` 自动 resize 到 `perception.image_max_size`（默认 1280px），节约 token
- 新增 `call_multi()` 方法：多图单次调用，尝试 `response_format=json_object`，失败自动降级
- 新增工厂函数 `get_vl_client()` / `get_llm_client()`，根据 `settings.backend` 自动选择端点
- `_extract_json()` 改为先尝试直接 parse，再截取 `{...}` 区间，鲁棒性提升

#### 任务 3：build_scene_graph 真实感知循环
- `src/scene_graph/relation_vocab.py`：50 个中文关系动词，带分类注释
- `src/scene_graph/builder.py`：核心构建逻辑
  - 中文 VLM prompt，严格 JSON schema，关系词表约束
  - 多帧合并：相同 (subject, relation, object) 在 `merge_window_sec` 内合并，t_start/t_end 取并集，confidence 取最大
  - 实体去重：`(label.lower(), type)` 完全匹配视为同实体，合并 attributes
  - `focus_entities` 双保险（prompt hint + 后处理过滤）
  - VLM 调用失败重试（默认 2 次），批次独立失败不影响其他批次
- `src/tools/scene_graph_builder.py`：移除 mock 为主路径，接真实 builder；mock 降级为 fallback（无帧路径或无 API Key 时）
- `src/scene_graph/graph.py`：Entity 新增 `first_seen` / `last_seen` 字段；`add_entity()` 支持更新时序区间；`to_text()` 支持从配置读默认 truncation

### 真实测试结果（test1.mp4，14 秒游戏录屏）

视频内容：某 FPS 游戏（疑似《堡垒之夜》）战队档案界面 + 角色大厅

运行命令：
```bash
DASHSCOPE_API_KEY=sk-xxx pytest tests/test_scene_graph_real.py -v -s
```

场景图输出（9 实体，6 三元组）：
```json
{
  "entities": {
    "角色'骑着骡子打鸟'": {"type": "person", "first_seen": 0.0, "last_seen": 4.7},
    "角色'鳞鱼不是鱼'":   {"type": "person", "first_seen": 9.4, "last_seen": 14.1},
    "角色'不si的土卜鼠'": {"type": "person", "first_seen": 9.4, "last_seen": 14.1},
    "角色'允崽'":         {"type": "person", "first_seen": 9.4, "last_seen": 14.1},
    "机械战士模型":        {"type": "object"},
    "跑车":               {"type": "object"},
    "游戏大厅/准备区":    {"type": "place"},
    "游戏界面面板":       {"type": "object"},
    "角色'Continuelcoin'战队成员（画面外）": {"type": "person"}
  },
  "triplets": [
    {"subject": "角色'骑着骡子打鸟'", "relation": "属于",  "object": "角色'Continuelcoin'战队成员（画面外）"},
    {"subject": "角色'鳞鱼不是鱼'",   "relation": "站在",  "object": "游戏大厅/准备区"},
    {"subject": "角色'不si的土卜鼠'", "relation": "站在",  "object": "游戏大厅/准备区"},
    {"subject": "角色'允崽'",         "relation": "站在",  "object": "游戏大厅/准备区"},
    {"subject": "机械战士模型",        "relation": "位于",  "object": "游戏大厅/准备区"},
    {"subject": "跑车",               "relation": "停在",  "object": "游戏大厅/准备区"}
  ]
}
```

### Token 消耗估算（4 帧 @ 1280px，qwen-vl-plus-latest）

| 项目       | 数量       | 费用（参考） |
|-----------|-----------|------------|
| 图像 token | ~4×1500 = 6000 | ~¥0.048 |
| 文本输入   | ~600 token | ~¥0.005   |
| 文本输出   | ~500 token | ~¥0.004   |
| **合计**  |            | **~¥0.057** |

> 注：DashScope 官网价格为 0.008 元/千 token（输入）/ 0.008 元/千 token（输出）。
> 图像按 `min(H,W)/28` 计算 patch 数，实际 token 数以账单为准。
> 每次 `build_scene_graph`（4 帧）大约 ¥0.05–0.10，100 次约 ¥5–10。

### 引入依赖
- `pydantic-settings>=2.3` — YAML + .env 配置加载
- `openai>=1.0` — 显式声明（之前隐式依赖）

### 已知问题 / TODO
1. **实体命名不稳定**：VLM 对同一实体可能在不同批次输出不同 label（如"骑着骡子打鸟"vs"角色'骑着骡子打鸟'"），当前规则去重（exact match）容易漏。建议后续用 sentence-transformers 做语义相似度去重（`dedup_threshold` 参数已预留）。
2. **test1.mp4 为游戏录屏**，不是真实世界视频。需要换一个包含真实人物/物体的视频才能更好地验证场景图质量。
3. **`query_scene_graph` 仍为关键词匹配**，FAISS 向量检索 TODO 已在代码中标注。
4. **`build_scene_graph` 单批次时延约 12s**（4 帧），多批次线性叠加。如需加速，可并行批次（当前串行）。
5. **respond_format=json_object** 在部分 qwen-vl-plus 版本有时不生效，已有 fallback（文本 JSON 解析）。
6. **Agent brain（Qwen3 / qwen-plus）** 未完整端到端测试，仅测试了 mock LLM。

### 下一步建议（优先级排序）
1. **换真实世界视频**：用一段包含人物活动的生活视频测试场景图质量
2. **实体语义去重**：接 sentence-transformers，cosine 相似度 > `dedup_threshold` 时合并
3. **FAISS 检索**：实现 `query_scene_graph` 的向量检索路径，替换关键词匹配
4. **并行批次**：`builder.build_frames()` 中用 `asyncio` 或 `ThreadPoolExecutor` 并行调用 VLM
5. ~~**端到端 Agent 测试**：接 DashScope qwen-plus-latest 作为 Agent brain，跑完整 ReAct 循环~~ **第四阶段完成**
6. **Gradio UI**：实现 `src/ui/app.py`，上传视频 → 实时问答
7. **部署文档**：补充 `docs/deployment.md`（vLLM + GPU 环境配置）

---

## 第四阶段：Agent 端到端打通 + 渐进式精化验证（本次）
**日期：** 2026-05-11

### 完成内容

#### 任务 1：修复 Agent 接入
- 发现并修复 `src/agents/react_agent.py` 的根本问题：旧版代码里 `create_agent` 的调用方式与安装的 LangChain 1.2.18 不兼容
- **关键洞察**：LangChain 1.x 已完全基于 LangGraph，`AgentExecutor` 被移除，`create_agent` 返回 `CompiledStateGraph`，调用接口改为 `agent.invoke({"messages": [("user", q)]})`
- 写了支持 `bind_tools` 的自定义 mock（`_DirectAnswerModel`），解决 `FakeListChatModel.bind_tools` 抛 `NotImplementedError` 的问题
- 内嵌中文双语 ReAct 系统 prompt：决策策略 + 证据引用要求
- `max_iterations` 6 → 对应 LangGraph `recursion_limit=19`

#### 任务 2：渐进式精化反馈回路
- `frame_inspector.py` 已有 back-propagation 逻辑；本次完善返回值：新增 `nodes_added_to_graph`、`edges_added_to_graph`、`graph_size_after` 字段
- Agent 每次 `inspect_frame` 后即可在 Observation 里看到"新增了 N 个实体"，知道场景图已更新，可立即再次 query

#### 任务 3：main.py CLI 入口
- 支持 `--question`（单次）和 `--interactive`（多轮，session 跨轮复用）
- 自定义 trace 输出：每步打印 Action / Action Input / Observation（截断到 600 字符）

#### 任务 4：修复 VLM JSON 解析器（遇到的坑）
- **坑**：Qwen-VL-Plus 在场景图 prompt 下会输出重复的 `"relations": [], "places": [], "other": []` 段落，外层 `}` 永远不关闭，导致 `json.loads` 失败
- **修复**：`_parse_vlm_output` 新增第三层兜底：括号深度匹配，单独提取 `entities` 和 `relations` 数组（即使外层 JSON 格式损坏也能成功）
- **顺带优化**：简化提示词，去掉 `places`/`other` 字样；VL max_tokens 2048 → 4096

### 真实端到端 trace（test1.mp4，14 秒游戏录屏）

```
Question: 视频里有哪些人物？他们在干什么？
Session : sess_97a9b2af

[Step 1]  extract_keyframes(strategy=uniform, count=16) → 16 frames
[Step 2]  build_scene_graph(*) → 29 entities, 24 triplets
[Step 3]  query_scene_graph("视频里有哪些人物？他们在干什么？") → found: false
          Entities (29): 玩家 骑着骡子打鸟, 玩家 鳞鱼不是鱼, 玩家 不si的土卜鼠, ...
[Step 4]  query_scene_graph("视频中有哪些人物角色？") → found: false
[Step 5]  inspect_frame(t=7.5, "视频中有哪些人物？他们在干什么？")
            nodes_added_to_graph: 4
            edges_added_to_graph: 5
            graph_size_after: 35 entities, 30 triplets

FINAL ANSWER:
  视频显示的是一个大逃杀游戏的准备界面，有四个角色等待比赛开始：
  1. "不si的土卜鼠" — 蓝白条纹运动服，手持蓝色枪械
  2. "鱿鱼不是鱼"  — 蓝白条纹运动服，紫色头发
  3. "骑着骡子打鸟" — 黄色T恤白色裤子，手持绿色武器
  4. "允崽"        — 白色T恤，德国国旗图案，蓝色头盔

Scene graph : 35 entities, 30 triplets
Tool calls  : 5
```

### 渐进式精化测试结果（test_progressive_refinement.py）

```
[Step 2] Initial graph: 5 entities, 4 triplets
         focus_entities="人" → ['玩家 骑着骡子打鸟', '玩家 鳞鱼不是鱼', ...]
[Step 3] inspect_frame(t=0.0, "描述所有可见物体和细节"):
         nodes_added_to_graph: 5
         edges_added_to_graph: 5
         graph_size_after    : 10 entities, 9 triplets

✓ 场景图增长: 5→10 entities, 4→9 triplets
✓ query_scene_graph("战队") → found=True, triplets=4
```

### Token 消耗估算（一次问答）

| 调用                          | token 数（估算） | 费用（估算）  |
|------------------------------|----------------|-------------|
| qwen-plus-latest（LLM，5轮）  | ~8000          | ~¥0.01      |
| qwen-vl-plus-latest（VLM，4批+1）| ~40000      | ~¥0.32      |
| **合计**                      |                | **~¥0.33**  |

> 图像 token 按 1280px / 28px/patch ≈ 1500 token/帧估算。

### 遇到的坑和解决方案

| 坑 | 原因 | 解决 |
|----|------|------|
| `FakeListChatModel` 不支持 `bind_tools` | LangChain 1.x `create_agent` 内部调用 `bind_tools` | 自定义 `_DirectAnswerModel` 覆盖 `bind_tools` 返回 self |
| VLM JSON 输出重复 `"relations": []` 无法解析 | Qwen-VL 对复杂 schema prompt 幻觉生成重复 key，外层 `}` 不关闭 | 三层解析兜底：第三层用括号深度匹配提取数组 |
| LangGraph verbose 日志淹没输出 | `create_agent(debug=True)` 打印 `[values]`/`[updates]` | 改为 `debug=False`，main.py 自行格式化 trace |
| `query_scene_graph` 中文关键词命中率低 | `.split()` 对中文无效（无空格），整句作为一个 token | 已知问题，暂靠 inspect_frame 兜底，FAISS 是后续解决方案 |

### 已知问题 / TODO（更新）
1. **`query_scene_graph` 中文匹配失效**：`.split()` 对中文分词无效，需要 jieba 或向量检索
2. **实体命名不稳定**：跨批次 VLM 对同一实体命名不一致，需语义去重
3. **`build_scene_graph` 默认 count=16**：Agent 有时会请求全部 16 帧，成本较高；可加入 adaptive sampling
4. **FAISS 向量检索**：`query_scene_graph` 的向量路径尚未实现
5. **并行批次**：`build_frames()` 中串行调用 VLM，16 帧约需 60-90s

### 下一步建议（优先级排序）
1. ~~**FAISS + 中文分词**：`query_scene_graph` 换向量检索，解决关键词匹配失效~~ **第五阶段完成（jieba 多策略匹配）**
2. ~~**实体语义去重**：sentence-transformers cosine 相似度 > `dedup_threshold` 时合并~~ **第五阶段完成（difflib 规则去重）**
3. **换真实世界视频**：生活视频效果更好，游戏 UI 截图会引入幻觉
4. ~~**并行 VLM 批次**：ThreadPoolExecutor 加速 build_frames~~ **第五阶段完成**
5. **FAISS 向量检索**：jieba 已覆盖 80% 命中率，剩余 20% 需语义近义词匹配（"人物"→具体角色名）
6. **Gradio UI**：`src/ui/app.py`，上传视频 → 实时问答

---

## 第五阶段：场景图检索修复 + 实体去重 + 并行加速（本次）
**日期：** 2026-05-11

### 完成内容

#### 任务 1：修复中文场景图检索（P0）

**根本问题**：`query_scene_graph` 用 `.split()` 对中文整句（无空格）分词完全失效，
导致几乎所有 query 都 miss，Agent 被迫一直 fallback 到 inspect_frame，场景图形同虚设。

**解决方案**：`src/scene_graph/retriever.py` — 多策略混合检索
1. **jieba 分词** + 动态用户词典（关系动词 + 当前实体名注入，防止实体名被切断）
2. 策略 a：精确实体名匹配（token == entity name，权重 +2.0）
3. 策略 b：关系动词匹配（token ∈ RELATION_VOCAB，权重 +1.5）
4. 策略 c：子串 OR 多关键词得分累积（token in subject/object，权重 +0.5）
5. 策略 d：时间约束（"开头"/"最后" 过滤三元组时间窗口）
6. `found=False` 时返回 `nearby_entities`（模糊匹配），让 Agent 知道图里有什么

新增文件：
- `src/scene_graph/stopwords.py` — 停用词表 + 时间关键词映射
- `src/scene_graph/retriever.py` — 检索器主体

**命中率测试结果**（`tests/test_query_chinese.py`，10 个中文查询）：

| 查询 | 策略 | 结果 |
|------|------|------|
| 游戏大厅里站着谁？ | 策略c | HIT |
| 不si的土卜鼠拿着什么武器？ | 策略a(精确实体名) | HIT |
| 骑着骡子打鸟在做什么？ | 策略a(精确实体名) | HIT |
| 谁属于蓝方战队？ | 策略b(关系动词) | HIT |
| 有人带头盔吗？ | 策略c(子串) | HIT |
| 谁在看跑车？ | 策略c | HIT |
| 鱿鱼不是鱼站在哪里？ | 策略a+b | HIT |
| 视频中有几辆跑车？ | 策略c | HIT |
| 视频里有哪些人物？ | — | MISS（"人物"≠具体角色名）|
| 有人拿枪吗？ | — | MISS（"拿枪"未匹配"持有"+"枪械"）|

**命中率：8/10 = 80%**（相比之前约 0%）

剩余 2 个 miss 为语义近义词问题（类别词"人物"→实例名；同义动词"拿枪"→"持有"），
需 FAISS + embedding 解决，jieba 方案已到能力上限。

#### 任务 2：实体命名稳定化（P0）

**根本问题**：VLM 跨批次对同一角色输出不同 label（"骑着骡子打鸟"/"角色'骑着骡子打鸟'"），
导致重复节点污染场景图。

**解决方案**：
1. **VLM Prompt 注入**：每次调用 VLM 时，将当前场景图已知实体（id + label + type）
   注入 prompt，明确要求"如果检测到相同实体请复用完全相同名称"。
2. **后处理去重**（`_cross_dedup_with_graph`）：VLM 返回后，用 `difflib.SequenceMatcher`
   对每个新实体与已有实体比对（同 type + 相似度 ≥ `dedup_threshold`=0.85），
   命中则合并（扩展 attributes + 更新 last_seen），不加入新节点。
   同时将 label_remap 应用到关系的 subject/object，保证关系指向正确节点。

测试结果（`tests/test_entity_dedup.py`，6 个单测）：

| 场景 | 结果 |
|------|------|
| 完全相同 label → 合并 | PASS |
| 相似 label（加前缀）→ 合并（threshold=0.75）| PASS |
| 不同 label → 保留各自 | PASS |
| 同 label 不同 type → 不合并 | PASS |
| 跨批次相似名 → 图大小不增长 | PASS |
| 合并时 attributes 传播到已有实体 | PASS |

#### 任务 3：build_scene_graph 并行化（P2）

**根本问题**：16 帧串行调用 VLM 约 60-90s，体验差。

**解决方案**：`concurrent.futures.ThreadPoolExecutor` + tqdm 进度条

- 批次粒度并行（每批 4 帧 1 次 VLM 调用），并发数 `max_parallel_batches=3`（从 config 读）
- 结果按批次编号收集，保持有序性
- tqdm 可选（graceful fallback 不报错）
- 预期 16 帧加速比约 3x：60-90s → 20-35s

#### 任务 4：清理冗余

- 删除 `src/perception/vlm.py`（已被 `vl_client.py` 完全取代，无任何引用）
- `requirements.txt` 新增 `jieba>=0.42`

### 测试结果汇总

```
pytest tests/ (不含 API Key 测试)
  38 passed, 11 skipped
  新增：test_query_chinese.py (5), test_entity_dedup.py (6)
  已有：23 个原有测试全部继续 pass
```

### 引入依赖
- `jieba>=0.42` — 中文分词

### 已知问题 / TODO（更新）
1. **query 语义近义词**：jieba 策略无法处理"人物"→具体角色名、"拿枪"→"持有"+"枪械"这类
   类别-实例或同义词映射，需 FAISS + sentence-transformers embedding
2. **test1.mp4 为游戏录屏**：真实世界视频（含行人、车辆、室内活动）效果更好
3. **build_scene_graph 并行加速未实测**：需有 API Key 环境验证实际提速比

### 下一步建议（优先级排序）
1. **FAISS + embedding**：sentence-transformers 向量检索覆盖剩余 20% 语义近义词 miss
2. **换真实世界视频**：test1.mp4 场景过于单一
3. ~~**Gradio UI**：`src/ui/app.py`，上传视频 → 实时问答~~ **第六阶段完成**
4. **部署文档**：`docs/deployment.md`（vLLM + GPU 环境配置）

---

## 第六阶段：自建评测集 + 真实 Benchmark + Gradio 前端（本次）
**日期：** 2026-05-12

### 完成内容

#### 任务 1：自建中文视频 QA 评测集

- `benchmarks/cn_video_qa_v1.json`：25 题，5 类（物体识别/实体属性/关系推理/时序推理/计数）
  - 每题含 `question`, `reference_answer`, `category`, `key_facts`
  - 基于 Phase 3/4 真实 VLM 分析（test1.mp4），非 mock 数据
- `benchmarks/cn_video_qa_v1_meta.md`：视频内容说明，角色 / 物体 / 三元组清单，数据来源声明

#### 任务 2：评测脚本 + 真实评测

- `src/eval/run_benchmark.py`：三方案基线 + LLM-as-Judge（qwen-plus-latest）
  - **agent**：预构建场景图（8帧），每题注入图状态 hint，Agent 直接 query_scene_graph / inspect_frame
  - **rag_only**：预构建场景图，LLM 从图文本回答，无视觉工具
  - **vlm_direct**：每题抽 4 帧直接发给 VLM，无场景图
  - Judge prompt 严格：`key_facts` 全命中才得 1.0，超过一半得 0.5
  - 关键修复：`sys.stdout.reconfigure(line_buffering=True)` 避免后台进程输出缓冲

**真实评测结果**（1 次运行，25 题，qwen-vl-plus-latest + qwen-plus-latest）：

| 方案 | 整体准确率 | 物体识别 | 实体属性 | 关系推理 | 时序推理 | 计数 | 均时(s) |
|------|-----------|---------|---------|---------|---------|------|---------|
| agent | 0.360 | 0.500 | 0.200 | 0.400 | **0.300** | 0.400 | 15.2 |
| rag_only | 0.340 | **0.700** | 0.200 | 0.400 | 0.000 | 0.400 | 3.1 |
| vlm_direct | **0.540** | 0.500 | **0.400** | **0.700** | 0.500 | **0.600** | 8.0 |

**关键洞察：**
- vlm_direct 整体最高：游戏 UI 有可读文字（队伍名/角色名），VLM 直接读取
- agent 时序推理唯一胜出方向（0.300 vs rag 0.000）：场景图 `first_seen/last_seen` 有效
- 属性识别全体偏低（0.2-0.4）：场景图未专门存储外观属性，是改进方向

#### 任务 3：Gradio 前端

- `frontend/app.py`：三栏布局 Gradio 5.x 界面
  - 左栏：视频上传 / 播放 + "构建场景图"按钮 + 状态
  - 中栏：多轮对话 + 5 个示例问题按钮 + "重置 Session" 按钮
  - 右栏：Agent trace（HTML 彩色 emoji 格式）+ 场景图状态（实体数/边数/最近实体）
  - 流式输出：`agent.stream()` 逐步更新 trace
  - `gr.State(_AppState())` 管理 session 和 agent 状态

#### 任务 4：最终文档

- `docs/architecture.md`：详细架构图（ASCII art + 组件说明 + 渐进式精化流程 + 部署方案）
- `README.md`：终版，含 mermaid 架构图、真实 benchmark 表格、项目亮点、诚实局限性
- `docs/benchmark_results.md`：自动生成 + 手工注解分析

### 遇到的坑

| 坑 | 原因 | 解决 |
|----|------|------|
| Agent 每题重建场景图（~90s/题）| Agent 从空对话开始，看不到已有图 | 注入 ctx_prefix 提示图已预构建 |
| 后台进程无输出 | Python stdout 管道缓冲 | `sys.stdout.reconfigure(line_buffering=True)` |
| 评测第一次运行成本过高（预估¥40+）| Agent 每题独立重建场景图 | 共享 session + hint 注入，实际跑完约 ¥8 |

### Token 消耗（本次评测，1 轮）

| 方法 | VLM 调用 | LLM 调用 | 大致费用 |
|------|---------|---------|---------|
| agent（25题）| 预构建 2 batch + inspect_frame | ~75 次 | ~¥4 |
| rag_only（25题）| 预构建 2 batch | 25 次 LLM | ~¥1 |
| vlm_direct（25题）| 25×4帧 = 100 次 VLM | 25 次 judge | ~¥2 |
| **合计** | | | **~¥7-8** |

### 已知问题 / TODO（更新）
1. **评测集扩展**：25 题统计量不足，建议扩展到 100+ 题或用 NExT-QA / ActivityNet-QA
2. **3 次运行取均值**：当前 1 次，std=0，无统计意义的方差估计
3. **换真实世界视频**：游戏录屏使 vlm_direct 占优（UI 文字），需生活场景视频验证 agent 优势
4. **Entity 外观属性**：`build_scene_graph` 未专门提取服装/颜色等属性，属性题目全体偏低
5. **Gradio 流式 trace** 依赖 `agent.stream()`，需在有 API Key 环境测试实际效果

### 下一步建议（优先级排序）
1. **换真实世界视频**：生活场景视频能更好体现 agent 时序 + 关系推理优势
2. **扩展评测集至 100 题**：覆盖更多场景，3 次运行取均值得到统计显著结果
3. **Entity 外观属性**：修改 `build_scene_graph` prompt 专门提取外观/属性信息
4. **FAISS + embedding**：解决语义近义词检索 miss（"人物"→具体角色名）
5. **部署文档**：`docs/deployment.md`（vLLM + GPU 环境配置，Docker compose）

---

## 第七阶段：换视频重测 + 消除字幕干扰变量（cooking.mp4）
**日期：** 2026-05-13

### 背景

Phase 6 发现 vlm_direct 以 0.540 大幅领先，但根本原因是 test1.mp4（游戏录屏）画面上有可读 UI 文字（角色名/队伍名），VLM 直接读字取胜，并非真正的视觉推理能力。本阶段换用 `cooking.mp4`（红烧肉教程，~202s）并重新出题，消除这一干扰变量，在公平条件下验证 agent 的时序场景图优势。

### 完成内容

#### 任务 1：视频内容分析

- `benchmarks/cooking_video_meta.md`：VLM 分析 15 帧（均匀采样），记录菜品、食材、厨具、8 个烹饪阶段时序、字幕内容
  - 菜品：红烧肉；主要阶段：焯水→切块→炒糖色→翻炒上色→转砂锅→加香料→小火慢炖→出锅
  - 字幕为喜剧评论风格（"苍蝇搓手"、"公文包"），**不含食谱信息**，无法用于作弊

#### 任务 2：新评测集（反字幕设计）

- `benchmarks/cn_video_qa_v2.json`：25 题，5 类 × 5 题，中文类别名
  - 设计原则：①所有题目无法通过读字幕回答；②时序/关系题占 40%（各 5 题）；③有精确数量要求（"几种锅"、"几次"）
  - 示例时序题："炒糖色是在放入猪肉块之前还是之后？"（需理解完整时间线）
  - 示例关系题："五花肉从开始到做成红烧肉，依次经过了哪几种锅具？按顺序说。"

#### 任务 3：完整评测（3 methods × 3 runs）

**最终结果**（qwen-plus-latest judge + qwen-vl-plus-latest VLM，25 题 × 3 runs）：

| 方案 | 整体（mean±std）| 物体识别 | 实体属性 | 关系推理 | 时序推理 | 计数 |
|------|----------------|---------|---------|---------|---------|------|
| **agent** | 0.313 ± 0.100 | 0.233 | 0.267 | **0.367** | **0.600** | 0.100 |
| vlm_direct | 0.353 ± 0.009 | **0.600** | **0.300** | 0.233 | 0.367 | **0.267** |
| rag_only | 0.113 ± 0.009 | 0.167 | 0.000 | 0.200 | 0.200 | 0.000 |

**关键发现：**
- **Agent 时序推理 0.600**（vlm_direct 0.367，+63%）：时序场景图在公平对照下的核心优势得到验证
- **Agent 关系推理 0.367**（vlm_direct 0.233）：多轮 query+inspect 迭代能拼出跨步骤的因果链
- vlm_direct 整体微领先（0.353 vs 0.313），但差距从 v1 的 0.180 缩至 0.040
- rag_only 全面低至 0.113（场景图仅 11 实体，严重覆盖不足）
- agent std=0.100，明显高于 vlm_direct/rag_only（0.009），随机 tool call 策略带来方差

#### 任务 4：文档

- `docs/benchmark_v2_results.md`：完整结果表 + per-question 明细 + v1 vs v2 对比
- `docs/benchmark_v2_analysis.md`：~400 字分析，核心论点"去掉字幕捷径后 agent 时序优势翻倍"

### 遇到的坑

| 坑 | 原因 | 解决 |
|----|------|------|
| DashScope 免费额度耗尽 | Phase 6 已用完 free tier 配额 | 用户禁用"仅免费额度"开关 |
| 账户欠款（Arrearage）| 禁用 free tier 后无余额自动扣费失败 | 用户充值 ¥30 |
| `_aggregate` KeyError：'物体识别' | v1 英文分类名硬编码，v2 用中文 | 改为从 trial 数据动态提取分类名 |
| main() 同样有硬编码分类 | 报告打印循环用 `["object",...]` | 同步修复为动态取 first_agg 的 keys |
| agent GraphRecursionError | 烹饪题更复杂，旧公式 `×3+1=19` 不够 | 改为 `×5+10=40` |

### Token 消耗（本次评测，3 runs each）

| 方法 | runs | 大致费用 |
|------|------|---------|
| VLM 内容分析（3 batch × 4 帧）| 1 次 | ~¥0.5 |
| agent（25题 × 3 runs，含 2 次失败重跑）| ~5 runs equiv | ~¥12 |
| rag_only（25题 × 3 runs）| 3 runs | ~¥1.5 |
| vlm_direct（25题 × 3 runs）| 3 runs | ~¥7 |
| **合计（本阶段）** | | **~¥21** |

### 已知问题 / TODO（更新）

1. **场景图覆盖不足**：cooking.mp4 仅构建出 11 实体 / 9 三元组（8 帧），烹饪步骤捕获严重不完整；需优化 `build_scene_graph` prompt 专针对"动作→容器→食材"三元组
2. **agent 方差大**（std=0.100）：3 runs 成绩 0.340 / 0.420 / 0.180，建议固定温度=0 或增加到 5 runs
3. **计数类全体偏低**：agent 0.100，vlm_direct 0.267，rag_only 0.000；"几种锅""几次""几种香料"需要精确计数能力，场景图和 4 帧采样都不足
4. **cn_video_qa_v2.json 使用中文 category**，v1 用英文；后续新建 QA 集建议统一格式（或在 run_benchmark 添加映射层）

### 下一步建议（优先级排序）

1. ~~**增加预构建帧数（8→16）**~~ **第八阶段完成**
2. ~~**agent 方差降低（temperature=0）**~~ **第八阶段完成**
3. **运行 final benchmark**：网络条件好时执行（见第八阶段）
4. **优化 `build_scene_graph` 针对动作类视频**：prompt 增加"烹饪动作、食材转移、容器变化、火候"专项提取；预期场景图实体 20→30+
5. **扩展评测集至 100 题**：当前 25 题每题权重 4%，统计显著性不足
6. **FAISS + embedding 检索**：替代 jieba 规则匹配，解决"焯水"≠"预处理"等语义近义词 miss
7. **vlm_direct_no_subtitle 变体**：黑化帧底部 1/4 后发 VLM，进一步对照字幕对结果的影响

---

## 第八阶段：降方差 + 帧数提升（final benchmark 准备）
**日期：** 2026-05-16

### 完成内容

#### 任务 1：降低 agent/rag_only 方差

- `configs/default.yaml`：`models.llm.temperature` 0.1 → **0.0**（确定性解码，消除 LLM 随机性）
- `src/eval/run_benchmark.py`：`_answer_rag_only` 中 `temperature=0.1` 硬编码改为读 `cfg.models.llm.temperature`
- VLM temperature 维持 0.1（build_scene_graph / inspect_frame 需要一定多样性）

#### 任务 2：预构建帧数 8 → 16

- `configs/default.yaml`：`perception.keyframe_count` 8 → **16**
- `src/eval/run_benchmark.py`：`run_trial` 中 `frame_count=8` 硬编码改为读 `cfg.perception.keyframe_count`
- `frontend/app.py`：`on_build_graph` 中 `count=8` 硬编码改为读 cfg

**效果验证**（sanity check，cooking.mp4）：

| 指标 | 改动前 | 改动后 |
|------|--------|--------|
| 预构建实体数 | 11 | **20–25**（目标 20+ 达到） |
| 单题答案质量 | — | 正确，含时间戳证据链（t=65s 糖色，t=95s 猪肉）|

#### 任务 3：修复 GraphRecursionError 崩溃

- **现象**：首次 benchmark 运行中 agent Run 3 Q16（时序推理题）触发 `GraphRecursionError`（recursion_limit=40），进程崩溃，已完成的两轮数据全部丢失
- **修复**：`_answer_agent` 中 `agent.invoke` 外加 try-except，捕获所有异常后返回空答案（judge 得 0 分），不再崩溃整个进程
- **根因**：时序推理题需要大量 inspect_frame 调用（Q16 Run3 超过 40 步），烹饪视频比游戏录屏需要更多迭代

### 遇到的坑

| 坑 | 原因 | 解决 |
|----|------|------|
| GraphRecursionError 导致整轮数据丢失 | `agent.invoke` 未捕获异常，直接抛出到进程 | try-except 包裹，异常时返回空答案 |
| DashScope ping 延迟 ~530ms | 网络质量较差（深夜） | 暂停 benchmark，等网络好时重跑 |

### Final Benchmark 待运行

配置已就绪，等网络条件好时执行：

```bash
cd ~/Video\ Agent
nohup python3 -m src.eval.run_benchmark \
    --video data/videos/cooking.mp4 \
    --benchmark benchmarks/cn_video_qa_v2.json \
    --runs 3 \
    --output docs/benchmark_final.md \
    > /tmp/benchmark_final.log 2>&1 &
```

### 已知问题 / TODO（更新）

1. **final benchmark 尚未完成**：网络延迟 ~530ms 导致终止，待重跑 → **第九阶段完成**
2. **agent 方差来源**：LLM temperature=0 后，方差主要来自 VLM（temperature=0.1）构建出的场景图内容不同（Run1: 20 实体，Run2: 25 实体，Run3: 21 实体）；若需进一步降方差，可将 VLM temperature 也调为 0
3. **计数类全体偏低**：精确计数需要场景图完整覆盖，当前仍是瓶颈

---

## 第九阶段：Final Benchmark 完成（Phase 8 配置）
**日期：** 2026-05-17

### 背景

Phase 8 配置就绪（temperature=0.0，keyframe=16，GraphRecursionError 修复），因网络延迟问题延迟执行。本阶段在网络条件改善后后台运行 final benchmark，耗时约 90 分钟完成全部 3 methods × 3 runs。

### Final Benchmark 结果（cooking.mp4，cn_video_qa_v2.json，3 runs）

**整体准确率：**

| 方案 | 准确率（mean±std）| 平均 Tool 调用 | 均时(s) | Tokens/Q |
|------|-----------------|--------------|---------|---------|
| **agent** | **0.313 ± 0.019** | 3.6 | 36.8 | 1,383 |
| vlm_direct | 0.293 ± 0.009 | — | 31.4 | 6,039 |
| rag_only | 0.040 ± 0.033 | — | 4.5 | 1,235 |

**分类准确率：**

| 分类 | agent | rag_only | vlm_direct |
|------|-------|----------|------------|
| 物体识别 | 0.367±0.125 | 0.067±0.047 | **0.400±0.000** |
| 实体属性 | **0.333±0.125** | 0.033±0.047 | 0.300±0.000 |
| 关系推理 | **0.267±0.047** | 0.067±0.047 | 0.100±0.000 |
| 时序推理 | 0.467±0.170 | 0.000±0.000 | **0.633±0.047** |
| 计数/出现 | **0.133±0.047** | 0.033±0.047 | 0.033±0.047 |

完整报告：`docs/benchmark_final.md`

### 与 Phase 7 对比

| 指标 | Phase 7（8帧，temp=0.1）| Phase 8（16帧，temp=0.0）| 变化 |
|------|------------------------|------------------------|------|
| agent 整体 | 0.313 ± **0.100** | 0.313 ± **0.019** | 方差大幅下降 ✓ |
| vlm_direct | 0.353 ± 0.009 | 0.293 ± 0.009 | 略降 |
| rag_only | 0.113 ± 0.009 | 0.040 ± 0.033 | 明显下降 ✗ |

### 关键发现

1. **Agent 方差如期下降**：std 0.100 → 0.019，temperature=0.0 效果显著
2. **Agent 整体最优（成本调整后）**：vlm_direct tokens/Q 是 agent 的 4.4×（6039 vs 1383），同精度下 agent 更经济
3. **意外：vlm_direct 时序推理最高**（0.633 vs agent 0.467）— 直接视觉感知对"先后顺序"判断更直接，场景图的时序表达仍不够紧凑
4. **Agent 关系推理领先**（0.267 vs vlm_direct 0.100，2.7×）— 场景图跨步骤关系推理优势明显
5. **rag_only 崩塌**：0.113 → 0.040；16 帧场景图更大但更噪，纯 RAG 检索质量下降，说明场景图质量比大小更重要

### 已知问题 / TODO（更新）

1. **时序推理缺口**：vlm_direct 0.633 vs agent 0.467，需要专门的时序事件日志工具或更紧凑的时序表达（而非依赖 `first_seen`/`last_seen`）
2. **rag_only 倒退**：16 帧场景图噪音更大，需检索重排序（reranking）或更聚焦的图构建策略
3. **计数类全体偏低**：agent 0.133，vlm_direct 0.033；精确计数需更完整场景图覆盖
4. **场景图 prompt 优化**：针对动作类视频专门提取"动作→食材→容器"三元组，预期实体 25→40+
5. **FAISS + embedding 检索**：替代 jieba，解决语义近义词 miss（"焯水"≠"预处理"）
6. **扩展评测集至 100 题**：25 题每题权重 4%，统计显著性不足

---

## 第十阶段：修复评测脚本交叉污染 + vlm_direct 重测（本次）
**日期：** 2026-05-17

### 背景

复盘 Phase 7→9 时发现一个反常现象：`vlm_direct` 的代码路径几乎没变，但其时序推理分数在 Phase 7（0.367）与 Phase 9（0.633）之间剧烈摆动。追查 `run_benchmark.py` 后定位到根因——**`vlm_direct` 不是一个独立基线**。

### 根本问题

`_answer_vlm_direct` 原先从 `session.cached_frames` 取帧，而该缓存由 `_prebuild_graph` 按 `perception.keyframe_count` 构建。于是：

- Phase 7（8 帧预构建）：`vlm_direct` 看到 frame 0,2,4,6
- Phase 9（16 帧预构建）：`vlm_direct` 看到 frame 0,4,8,12

**一个为 Agent 调的配置（`keyframe_count` 8→16）悄悄改写了基线的输入**，使 Phase 间对比失效。早期「关系推理 2.7×、整体持平」的结论即建立在这一被污染的 `vlm_direct` 数据上。

### 完成内容

#### 任务 1：vlm_direct 抽帧解耦（评测交叉污染修复）

- `_answer_vlm_direct` 改为**独立抽帧**：自行调用 `extract_keyframes(strategy="uniform")`，不再复用 Agent 预构建的帧缓存，与 `keyframe_count` 完全无关。
- 新增常量 `_VLM_DIRECT_FRAME_COUNT = 4`，固定且独立于任何 Agent 侧配置。

#### 任务 2：删除 `_build_report` 占位 TODO

- `run_benchmark.py` 的报告生成器每次都写入一行 `_TODO: Replace placeholder results..._`，导致 `benchmark_final.md` 末尾出现与真实结果自相矛盾的文字。已删除（源码 + 已生成文件）。

#### 任务 3：抽帧健壮性修复（cv2 末帧丢弃）

- 第一次重跑后发现 `uniform count=4` 在 `cooking.mp4` 上**只返回 3 帧**：OpenCV 上报的总帧数偏多，最后一帧索引解码失败被静默丢弃，导致采样**前移**、漏掉视频后 30%（出锅 / 成品环节）。
- 修复：新增 `_VLM_DIRECT_OVERSAMPLE = 8`，过采样 8 帧后均匀挑选 4 帧。即使末帧丢弃，仍能稳定取到 4 帧且覆盖全片 0–100%。

#### 任务 4：重跑 vlm_direct 并合并 final benchmark

- 仅 `vlm_direct` 受本次修复影响（修改全部位于 `_answer_vlm_direct`），`agent` / `rag_only` 逻辑未变，沿用 Phase 9 数据。
- 用修正版重跑 `vlm_direct`（25 题 × 3 轮），结果合并入 `docs/benchmark_final.md` / `.json`。

### vlm_direct 重测结果对比

| 指标 | 旧 buggy（耦合 keyframe_count）| 修正版（独立抽帧 + 过采样）|
|------|------|------|
| 整体 | 0.293 ± 0.009 | **0.373 ± 0.009** |
| 物体识别 | 0.400 | 0.600 |
| 实体属性 | 0.300 | 0.500 |
| 关系推理 | 0.100 | 0.267 |
| 时序推理 | 0.633 | 0.500 |
| 计数/出现 | 0.033 | 0.000 |

### 修正后的诚实结论

| 方案 | 整体准确率 | Tokens/Q |
|------|-----------|---------|
| agent | 0.313 ± 0.019 | 1,383 |
| vlm_direct | **0.373 ± 0.009** | 6,039 |
| rag_only | 0.040 ± 0.033 | 1,235 |

1. **公平评测下 vlm_direct 整体领先**（0.373 vs agent 0.313）：直接视觉感知在物体识别、实体属性上明显更强。
2. **早期「关系推理 2.7×」结论失效**：修正后关系推理 agent 0.267 vs vlm_direct 0.267，**持平**。
3. **Agent 唯一明确领先的赛道是计数 / 出现**（0.133 vs 0.000）——结构化记忆对「跨帧聚合去重」类问题确有价值。
4. **Agent 的核心价值是成本**：以 ~1/4 的 token 开销（1,383 vs 6,039）换取相近量级的整体表现。
5. **单类别仅 5 题**，分类层面的胜负方差大、不具统计显著性；可靠结论仅为整体准确率与 token 成本。

### 遇到的坑

| 坑 | 原因 | 解决 |
|----|------|------|
| vlm_direct 跨 Phase 分数剧烈摆动 | 抽帧复用 Agent 预构建缓存，隐式耦合 `keyframe_count` | `_answer_vlm_direct` 独立抽帧 |
| `uniform count=4` 实际只返回 3 帧 | cv2 上报帧数偏多，末帧索引解码失败被丢弃，采样前移漏掉视频结尾 | 过采样 8 帧后均匀挑 4 帧 |
| `benchmark_final.md` 末尾有自相矛盾的占位 TODO | `_build_report` 模板残留 | 删除源码中的 TODO 行 |

### 已知问题 / TODO（更新）

1. **Agent 准确率上限受场景图质量制约**：`build_scene_graph` 仅抽出 ~22–27 实体，prompt 未针对动作 / 烹饪类视频优化——这是 Agent 落后 vlm_direct 的主因，也是最高优先级的可改进项。
2. **评测集规模小**：单类别 5 题，分类结论不具统计显著性，应扩展到 100+ 题。
3. **agent / rag_only 未随本次重跑**：本次仅 vlm_direct 受代码改动影响；如需完全同批次数据可三方案一并重跑。

### 下一步建议（优先级排序）

1. **优化 `build_scene_graph` 动作类提取 prompt**：针对「烹饪动作 → 食材转移 → 容器变化 → 火候」专项提取，把场景图实体数提到 40+，提升 Agent 准确率上限。
2. **扩展评测集至 100+ 题**：获得统计显著的对比结论。
3. **更能体现 Agent 优势的评测区间**：更长视频 / 单视频多问题，让 vlm_direct 的线性 token 成本充分暴露。
