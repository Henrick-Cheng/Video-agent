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
# TODO: fill in after environment setup
pip install -r requirements.txt

# Mock demo (no GPU / model required)
python -m examples.demo --video path/to/video.mp4 --question "视频中发生了什么？"

# Real mode (requires vLLM servers)
# Terminal 1: serve VLM
vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ --api-key token-abc --port 8001

# Terminal 2: serve LLM
vllm serve Qwen/Qwen3-8B --api-key token-abc --port 8000

# Terminal 3: run agent
python main.py --video path/to/video.mp4 --question "..."
```

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
