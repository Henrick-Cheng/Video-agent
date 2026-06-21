# MMBench-Video 最终结果（runs=3）—— mmbv 线收尾

> 数据：`benchmarks/mmbv_150.json`（150 题 / 136 视频，分层抽样 seed=42）×
> {agent_v2, vlm_transcript@8, vlm_direct@8} × **runs=3**。
> 评分：官方 VLMEvalKit 0–3 协议，judge = `qwen-max`（测试口径）。
> Token / frames 全部真实 API usage。原始：`docs/benchmark_mmbv_final.json`。
> **这是 mmbv 上的权威结果，可供论文 / 简历引用。**

## 总览（mean ± std over 3 runs）

| 方法 | 总分 (0–3) | Frames/Q |
|---|---|---|
| **agent_v2**（Lazy 记忆 + 置信度探索） | **1.984 ± 0.101** | **3.1** |
| vlm_transcript@8（同帧数 + 旁白，公平基线） | 1.727 ± 0.020 | 8.0 |
| vlm_direct@8（直接看帧） | 1.478 ± 0.025 | 8.0 |

## 反超抗噪 —— 成立

- agent_v2 − vlm_transcript = **0.257** > 两者 std 之和 **0.121** → **反超越过噪声带，为真**。
- agent_v2 的 std（0.101）大于基线（探索路径随机性，temp=0.1），但 gap 仍稳过。

## 归因（runs=3 复核，与 runs=1 几乎一致）

- **ASR 模态**：vlm_direct 1.478 → vlm_transcript 1.727（**+0.249**）
- **架构（同模态对照）**：vlm_transcript 1.727 → agent_v2 1.984（**+0.257**）
- 模态与架构贡献各半，"赢只靠多个模态"被公平基线排除。

## 舒适区（时长桶 × 方法，runs=3）

| 桶 | agent_v2 | vlm_transcript | vlm_direct |
|---|---|---|---|
| <90s (n=52) | 1.81 | 1.76 | 1.57 |
| 90-180s (n=50) | **2.10** | 1.55 | 1.34 |
| >180s (n=48) | **2.05** | 1.87 | 1.52 |

边界 ≈90 秒：90 秒内基本持平，90 秒以上明显领先。

## 关键维度（runs=3）

- **HL 幻觉抵抗**：agent_v2 **2.422±0.191** vs vlm_transcript 1.044 vs vlm_direct 0.622（约 2.3× / 3.9×）——机制性优势，最硬的卖点。
- **FP-C 跨实例**：1.489 vs 0.756（~2×）；**CP** 2.244 vs 1.600；**FP-S** 2.040 vs 1.667。
- 输的维度：**TR** 1.544 < vlm_transcript 1.767（TR 增益主要来自模态而非架构）、RR/CSR/AR 基线+旁白有竞争力。

## 标注天花板（annotation_audit, n=30, seed=11）

- 抽 30 题判 gold 是否被「L0 摘要 + 完整旁白」支撑：**supported 29 (97%) / partial 1 / unsupported 0** → 粗略天花板 ~0.98（归一）。
- 含义：**金标准基本干净，0434 那种 gold-与证据对不上是少数**；agent_v2(1.984/3.0 ≈ 0.66) 离天花板的差距**主要是真实能力差距（VLM 意图/因果推理 + 长视频定位），不是烂标注**。
- ⚠️ PROXY 披露：审计用 LLM（qwen）按摘要+旁白判定、偏宽松，且需细视觉的题可能被高估为 supported；以已知的 0434 锚定其真实存在但稀少。

## 披露

- judge = qwen-max（存在 Qwen 评 Qwen 自偏好）；**gpt-4-turbo 论文级重评待 OpenAI key**，脚本 `scripts/rejudge_gpt4.py` 已就绪、零推理成本（只评缓存答案）。
- runs=3 ±std；成本：agent_v2 仍约基线 2.1×（卖点是帧效率 3.1 vs 8 + 90s+ 准确率，非成本）。

## mmbv 线结论（收尾）

v2 在 MMBench-Video 上对直接看帧基线的反超 **runs=3 抗噪成立**（1.984 ± 0.101 vs 1.727 ± 0.020），归因干净、舒适区清晰、幻觉抵抗 2× 起。**mmbv 上的便宜提升杠杆已耗尽**（Phase 14.1 路由证伪、14.2 取证深度证伪），残差是 VLM 能力天花板 + 长视频定位（🔴 locate_visual / D6 窄窗加密均已评估为不划算，**DROPPED，非未来工作**）。

**要更强证据应换数据集复现，而非榨本集残差**：下一迭代方向 = 更干净 / 更长的公开基准（EgoSchema / Video-MME long）复现同一反超。
