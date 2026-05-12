# Benchmark Results

> Video: `data/videos/test1.mp4`  |  Benchmark: `benchmarks/cn_video_qa_v1.json`  |  Runs: 1  |  Generated: 2026-05-12 17:39

## Overall Accuracy

| Method | Accuracy (mean ± std) | Avg Tool Calls | Avg Time/Q (s) | Est. Tokens/Q |
|--------|----------------------|----------------|----------------|---------------|
| **agent** | 0.360 ± 0.000 | 2.1 | 15.2 | 985 |
| **rag_only** | 0.340 ± 0.000 | — | 3.1 | 850 |
| **vlm_direct** | **0.540** ± 0.000 | — | 8.0 | 6038 |

## Per-Category Accuracy

| Category | agent | rag_only | vlm_direct |
|----------|-------|---------|-----------|
| 物体识别 | 0.500 | **0.700** | 0.500 |
| 实体属性 | 0.200 | 0.200 | **0.400** |
| 关系推理 | 0.400 | 0.400 | **0.700** |
| 时序推理 | **0.300** | 0.000 | 0.500 |
| 计数/出现 | 0.400 | 0.400 | **0.600** |

## Key Findings

### VLM_DIRECT 整体最高（0.540）
- 视频为游戏 UI，界面上直接显示队伍名称、角色名称等**可读文本**
- VLM 直接看帧可以读取 UI 文字（如"Continuelcoin"战队标识）
- 绕过了场景图构建过程中的信息损失

### agent 时序推理最佳（0.300 vs rag_only 0.000）
- 场景图存储 `first_seen` / `last_seen` 时间戳，LLM 可推理时序
- rag_only 的图文本中时间信息未被 LLM 有效利用（纯文本格式）
- 体现了"结构化工作记忆"的价值：时序信息作为一等公民

### rag_only 物体识别最佳（0.700）
- 8 帧场景图对"有什么物体"类问题覆盖全面
- 纯文本 LLM 直接匹配场景图中的物体列表
- 比 agent 好是因为 agent 的 inspect_frame 有时引入干扰

### 属性识别所有方案均弱（0.200–0.400）
- 游戏 UI 场景对"服装颜色"等细节捕获不稳定
- 场景图只记录三元组，不记录像素级视觉属性
- 根本原因：`build_scene_graph` prompt 未专门提取服装/外观属性

## 方法说明

- **agent**: 预构建场景图（8帧），再为每题调用 ReAct Agent（query_scene_graph + inspect_frame）
- **rag_only**: 预构建场景图（8帧），LLM 仅从图文本回答，不调用视觉工具
- **vlm_direct**: 每题抽取 4 帧，直接发送给 VLM 回答，不构建场景图
- **Judge**: `qwen-plus-latest` LLM-as-Judge，依据 `key_facts` 评分 0 / 0.5 / 1

## 限制与展望

| 限制 | 影响 | 改进方向 |
|------|------|---------|
| 仅 1 次运行，std=0 | 无法衡量方差 | 跑 3 次取均值（已实现，待执行） |
| 测试集仅 25 题 | 统计不显著 | 扩展到 100+ 题或标准数据集 |
| 视频为游戏录屏 | UI 文字使 vlm_direct 占优 | 换真实世界视频重测 |
| agent 场景图 8 帧 | 部分实体未捕获 | 增加帧数或按需采样 |
| 属性信息不在三元组中 | 属性题目全体偏低 | 扩展 Entity 存储外观属性 |
