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
5. **端到端 Agent 测试**：接 DashScope qwen-plus-latest 作为 Agent brain，跑完整 ReAct 循环
6. **Gradio UI**：实现 `src/ui/app.py`，上传视频 → 实时问答
7. **部署文档**：补充 `docs/deployment.md`（vLLM + GPU 环境配置）
