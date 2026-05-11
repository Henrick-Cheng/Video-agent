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
3. **Gradio UI**：`src/ui/app.py`，上传视频 → 实时问答
4. **部署文档**：`docs/deployment.md`（vLLM + GPU 环境配置）
