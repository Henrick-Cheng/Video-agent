# Video Agent: Multimodal Video Understanding with Scene Graphs

> A ReAct-based Agent system that uses temporal scene graphs as structured working memory for video question answering.

## Architecture

```
                         ┌─────────────────────────────┐
                         │         User Question        │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │      Qwen3-8B ReAct Agent    │
                         │  (reasons, selects tools)    │
                         └──┬───────┬───────┬───────┬──┘
                            │       │       │       │
              ┌─────────────▼─┐ ┌───▼───┐ ┌─▼───┐ ┌▼────────────┐
              │ extract_      │ │ build_│ │query│ │inspect_     │
              │ keyframes     │ │ scene_│ │scene│ │frame        │
              │               │ │ graph │ │graph│ │(VLM精读)    │
              └───────┬───────┘ └───┬───┘ └──┬──┘ └──────┬──────┘
                      │             │         │            │
              ┌───────▼─────────────▼─────────▼────────────▼──────┐
              │                  VideoSession                       │
              │        (shared state: scene graph + frames)        │
              └────────────────────────────────────────────────────┘
```

**Key insight:** The scene graph acts as the Agent's structured working memory. The Agent builds it lazily (only the parts it needs), and `inspect_frame` discoveries back-propagate into it.

Triplet format: `<subject, relation, object, t_start, t_end>`

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # add your DASHSCOPE_API_KEY

# DashScope 云端模式（推荐开发 / macOS）
python main.py --video data/videos/test1.mp4 --question "视频里有哪些人物？"

# 多轮交互模式（跨轮复用场景图）
python main.py --video data/videos/test1.mp4 --interactive

# 离线 mock 模式（无需 API Key / GPU）
python main.py --video path/to/video.mp4 --question "..." --mock
python -m examples.demo --video path/to/video.mp4 --question "视频中发生了什么？"

# 本地 vLLM 模式（生产 / GPU 机器）
# Terminal 1: vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ --api-key token-abc --port 8001
# Terminal 2: vllm serve Qwen/Qwen3-8B --api-key token-abc --port 8000
python main.py --video ... --question "..." --backend vllm
```

### 渐进式精化演示（图-像双向迭代）

下面是一次真实运行的 trace（`test1.mp4`，14 秒游戏录屏，`qwen-plus-latest` + `qwen-vl-plus-latest`）：

```
[Step 1]  extract_keyframes → 16 frames cached
[Step 2]  build_scene_graph(*) → 29 entities, 24 triplets
[Step 3]  query_scene_graph("视频里有哪些人物") → found: false (keyword 未命中)
[Step 4]  query_scene_graph("视频中有哪些人物角色") → found: false
[Step 5]  inspect_frame(t=7.5, "视频中有哪些人物？") →
            nodes_added_to_graph: 4
            edges_added_to_graph: 5
            graph_size_after: 35 entities, 30 triplets

FINAL ANSWER:
  视频中有四个游戏角色，正在等待比赛开始：
  1. "不si的土卜鼠" — 蓝白条纹运动服，手持蓝色枪械
  2. "鱿鱼不是鱼"  — 蓝白条纹运动服，紫色头发
  3. "骑着骡子打鸟" — 黄色T恤白色裤子，手持绿色武器
  4. "允崽"        — 白色T恤，带德国国旗图案，蓝色头盔
  (Scene graph: 35 entities, 30 triplets | 5 tool calls)
```

**渐进式精化**：`build_scene_graph` 初建图（N1）→ `inspect_frame` 精读单帧 → 新发现自动反向写入场景图（N2 > N1）→ 后续 `query_scene_graph` 可直接查到新内容。见 `tests/test_progressive_refinement.py` 的端到端验证（5→10 entities）。

## Method Comparison

| Method | Scene Graph | Agent | Adaptive Sampling | Back-propagation |
|--------|-------------|-------|-------------------|-----------------|
| Fixed pipeline | ✗ | ✗ | ✗ | ✗ |
| Video-LLaVA | ✗ | ✗ | ✗ | ✗ |
| **Video Agent (ours)** | ✓ | ✓ | ✓ | ✓ |

_TODO: fill in benchmark results on NExT-QA / ActivityNet-QA_

## Project Structure

```
src/
├── agents/         # ReAct Agent factory and prompt templates
├── tools/          # 4 LangChain tools (extract / build / query / inspect)
├── perception/     # Qwen2.5-VL-7B-AWQ wrapper
├── scene_graph/    # Triplet dataclass + SceneGraph data structure
├── memory/         # VideoSession: shared state container
└── eval/           # QA evaluation metrics
```

## Hardware

Targeting single 24 GB GPU (RTX 4090 or equivalent).
Qwen2.5-VL-7B-AWQ and Qwen3-8B can be served simultaneously with AWQ quantization.
