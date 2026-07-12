# Benchmark V2 Results — cooking.mp4

> Video: `data/videos/cooking.mp4` (红烧肉教程, ~202s)  
> Benchmark: `benchmarks/cn_video_qa_v2.json` (25 QA pairs, 5 categories)  
> Runs: 3 per method | Judge: `qwen-plus-latest` LLM-as-Judge  
> Generated: 2026-05-13

---

## Overall Accuracy

| Method | Accuracy (mean ± std) | Avg Time/Q (s) | Est. Tokens/Q |
|--------|----------------------|----------------|---------------|
| **agent** | **0.313 ± 0.100** | ~37 | ~1200 |
| vlm_direct | 0.353 ± 0.009 | ~7 | ~6040 |
| rag_only | 0.113 ± 0.009 | ~4 | ~737 |

---

## Per-Category Accuracy

| Category | agent | vlm_direct | rag_only |
|----------|-------|-----------|---------|
| 物体识别 | 0.233 ± 0.170 | **0.600 ± 0.000** | 0.167 ± 0.047 |
| 实体属性 | 0.267 ± 0.170 | **0.300 ± 0.000** | 0.000 ± 0.000 |
| 关系推理 | **0.367 ± 0.170** | 0.233 ± 0.047 | 0.200 ± 0.082 |
| 时序推理 | **0.600 ± 0.082** | 0.367 ± 0.047 | 0.200 ± 0.082 |
| 计数/出现 | 0.100 ± 0.082 | **0.267 ± 0.047** | 0.000 ± 0.000 |

> **Bold** = best in category

---

## Key Findings

### Agent 时序推理最强（0.600，领先 vlm_direct 63%）

- 场景图存储 `first_seen` / `last_seen` 时间戳，LLM 可直接推断"A在B之前/之后"
- 时序题（如"炒糖色是在放猪肉前还是后？"）在所有 3 runs 都稳定得分，std=0.082 最低
- rag_only 的图文本中时序结构未被 LLM 有效利用（0.200）

### Agent 关系推理领先（0.367 vs vlm_direct 0.233）

- 关系题要求跨步骤推理（如"依次用了哪几种锅"），Agent 通过多次 query+inspect 迭代逐步构建答案
- vlm_direct 仅看 4 帧，难以覆盖完整的锅具使用顺序

### vlm_direct 物体识别最佳（0.600）

- cooking.mp4 无可读 UI 文字，但 VLM 直接看帧能识别食材外观（葱花、五花肉等）
- 场景图（11 实体 / 9 三元组）覆盖有限，agent 在物体识别上表现受限

### rag_only 全面偏低（0.113）

- 场景图仅 11 实体，对"放了什么香料""用了几种锅"等问题缺乏足够信息
- 没有 inspect_frame 工具，无法补充未被场景图捕获的内容
- 实体属性和计数类别得 0.000，说明稀疏场景图对 RAG-only 方案是瓶颈

### Agent 方差大（std=0.100），rag_only/vlm_direct 稳定（std≈0.009）

- Agent 3 runs 成绩：0.340 / 0.420 / 0.180，方差来自随机 tool call 策略
- vlm_direct/rag_only 基于确定性（贪心解码），仅 judge 随机性引入微小方差

---

## 对比 V1（test1.mp4 游戏录屏）

| 维度 | V1 test1.mp4 | V2 cooking.mp4 |
|------|-------------|----------------|
| Agent 整体 | 0.360 | 0.313 |
| rag_only 整体 | 0.340 | 0.113 |
| vlm_direct 整体 | **0.540** | 0.353 |
| Agent 时序推理 | **0.300** | **0.600** |
| vlm_direct 时序推理 | 0.500 | 0.367 |
| vlm_direct 优势来源 | 读 UI 文字 | 直接视觉识别 |
| Agent vs vlm_direct | -0.180 | -0.040（差距大幅缩小） |

**关键结论**：去掉"可读字幕"变量后，agent 与 vlm_direct 差距从 0.180 缩小至 0.040；
agent 时序推理从 0.300 跃升至 0.600，验证了时序场景图在公平评测环境下的核心优势。

---

## 方法说明

- **agent**: 预构建场景图（8帧），每题调用 ReAct Agent（query_scene_graph + inspect_frame）
- **rag_only**: 预构建场景图（8帧），LLM 仅从图文本回答，不调用视觉工具
- **vlm_direct**: 预提取帧（8帧），每题抽 4 帧直接发 VLM
- **Judge**: `qwen-plus-latest` LLM-as-Judge，依据 `key_facts` 评分 0 / 0.5 / 1

---

## 限制与展望

| 限制 | 影响 | 改进方向 |
|------|------|---------|
| 场景图仅 11 实体 | Agent 关键知识缺失，物体/计数类偏低 | 增加预构建帧数 8→16，优化 prompt 针对烹饪场景 |
| Agent std=0.100 | 3 runs 方差大，结论不够稳定 | 增加到 5 runs 或使用温度=0 |
| 测试集仅 25 题 | 每题权重 4%，统计显著性有限 | 扩展到 100 题 |
| 单视频单菜品 | 泛化性未验证 | 换多种烹饪场景（炒/炖/烤）重测 |
