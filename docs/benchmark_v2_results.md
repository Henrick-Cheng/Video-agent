# Benchmark V2 Results — cooking.mp4

> Video: `data/videos/cooking.mp4` (红烧肉教程, ~202s)  
> Benchmark: `benchmarks/cn_video_qa_v2.json` (25 QA pairs)  
> Status: **Partial** — agent run 1 complete; runs 2–3 and rag_only/vlm_direct pending DashScope quota fix  
> Generated: 2026-05-13

---

## Overall Accuracy

| Method | Accuracy (mean ± std) | Avg Tool Calls | Avg Time/Q (s) | Est. Tokens/Q |
|--------|----------------------|----------------|----------------|---------------|
| **agent** | 0.220 ± — (1 run) | 3.8 | 43.5 | ~1200 |
| **rag_only** | TBD | — | ~3 | ~850 |
| **vlm_direct** | TBD | — | ~8 | ~6000 |

> Note: Only agent run 1 completed before DashScope free tier quota exhausted.  
> Run `python -m src.eval.run_benchmark --video data/videos/cooking.mp4 --benchmark benchmarks/cn_video_qa_v2.json --runs 3 --output docs/benchmark_v2_results.md` to regenerate after fixing quota.

---

## Per-Category Accuracy (Agent, Run 1)

| Category | agent (run 1) | rag_only | vlm_direct |
|----------|---------------|---------|-----------|
| 物体识别 | 0.200 | TBD | TBD |
| 实体属性 | 0.300 | TBD | TBD |
| 关系推理 | 0.100 | TBD | TBD |
| 时序推理 | 0.300 | TBD | TBD |
| 计数/出现 | 0.200 | TBD | TBD |
| **Overall** | **0.220** | TBD | TBD |

---

## Per-Question Scores (Agent Run 1)

| ID | Category | Question | Score | Time | Tools |
|----|----------|---------|-------|------|-------|
| v2_obj_01 | 物体识别 | 视频中一共出现了哪几种不同的锅具？ | 0.0 | 8.2s | 1 |
| v2_obj_02 | 物体识别 | 视频中放入砂锅的香料有哪些？ | 0.0 | 80.4s | 5 |
| v2_obj_03 | 物体识别 | 视频中炒糖色使用的是哪种糖？ | 0.0 | 18.8s | 2 |
| v2_obj_04 | 物体识别 | 五花肉焯水时锅里除了肉还放了什么？ | 0.0 | 25.0s | 2 |
| v2_obj_05 | 物体识别 | 视频中最后出锅时在红烧肉上撒了什么？ | 1.0 | 42.0s | 4 |
| v2_attr_01 | 实体属性 | 慢炖阶段使用的是什么火候？ | 0.5 | 64.8s | 5 |
| v2_attr_02 | 实体属性 | 五花肉在切块之前是什么状态？对它做了什么处理？ | 0.5 | 27.6s | 4 |
| v2_attr_03 | 实体属性 | 视频中加入砂锅的香料是如何放置的？ | 0.0 | 99.4s | 9 |
| v2_attr_04 | 实体属性 | 视频最后用什么展示了红烧肉的成品质感？ | 0.0 | 20.1s | 2 |
| v2_attr_05 | 实体属性 | 炒糖色时使用的是什么火候？ | 0.5 | 49.6s | 3 |
| v2_rel_01 | 关系推理 | 五花肉依次经过了哪几种锅具？按顺序说。 | 0.0 | 59.1s | 5 |
| v2_rel_02 | 关系推理 | 冰糖在这道菜中起什么作用？ | 0.5 | 119.7s | 7 |
| v2_rel_03 | 关系推理 | 葱在这个视频中有几种不同用途？ | 0.0 | 17.2s | 2 |
| v2_rel_04 | 关系推理 | 酱油是在哪个阶段、用哪种锅加入的？ | 0.0 | 16.5s | 2 |
| v2_rel_05 | 关系推理 | 哪些食材是在同一时间一起加入砂锅的？ | 0.0 | 19.1s | 2 |
| v2_temp_01 | 时序推理 | 炒糖色是在放入猪肉块之前还是之后？ | 0.0 | 152.3s | 11 |
| v2_temp_02 | 时序推理 | 香料是在五花肉转入砂锅之前还是之后加入的？ | 0.0 | 91.8s | 10 |
| v2_temp_03 | 时序推理 | 五花肉是先焯水还是先切块？ | 0.0 | 5.8s | 0 |
| v2_temp_04 | 时序推理 | 葱花是在什么时候加入的？ | 1.0 | 8.3s | 1 |
| v2_temp_05 | 时序推理 | 视频中焯水步骤和炒糖色步骤，哪个先发生？ | 0.5 | 27.8s | 5 |
| v2_count_01 | 计数/出现 | 视频中五花肉经历了几个主要的烹饪阶段？ | 0.5 | 23.2s | 5 |
| v2_count_02 | 计数/出现 | 视频中放入的干香料共有几种？ | 0.0 | 24.9s | 3 |
| v2_count_03 | 计数/出现 | 葱在整个烹饪过程中被加入了几次？ | 0.0 | 7.6s | 1 |
| v2_count_04 | 计数/出现 | 视频中出现了几种液体调料（不含清水）？ | 0.0 | 9.4s | 1 |
| v2_count_05 | 计数/出现 | 视频中总共使用了几种不同的烹饪工具？ | 0.5 | 42.9s | 7 |

---

## Key Observations (Preliminary, Agent Run 1 Only)

### Agent整体偏低（0.220）的根本原因
场景图仅 11 实体、9 条三元组，远不足以覆盖红烧肉的完整烹饪步骤。
cooking.mp4 内容密度高（8个烹饪阶段 × 多种食材），而 8 帧均匀采样难以捕获所有关键信息。

### 时序推理相对较好（0.300）
- Q19（葱花最后加入）和 Q20（焯水→炒糖色顺序）得分，说明场景图时间戳仍有价值
- Q16/Q17（复杂时序 + 多工具 call）耗时最长（90–152s），用了10–11次工具调用仍失败

### 关系推理最弱（0.100）
- 需要跨多个步骤推理（"先A锅再B锅再C锅"）
- 场景图覆盖不足，agent频繁调用 inspect_frame 但 VLM 分析仍有信息缺失

### 物体识别出乎意料低（0.200）
- cooking.mp4 没有可直读的文字 UI，VLM 需要真正识别视觉内容
- 场景图预构建 8 帧，未能捕获砂锅/炒锅等多种锅具的完整出现序列

---

## Limitations

| Limitation | Impact |
|-----------|--------|
| 仅 1 次 agent 运行，无方差数据 | 无法判断稳定性 |
| rag_only / vlm_direct 未运行 | 无法对比三种方案 |
| 场景图仅 11 实体（应 >30） | Agent 严重缺乏背景知识 |
| 8 帧采样不足于 202s 视频 | 细节步骤（炒糖色、加香料）可能被遗漏 |

---

## How to Complete the Benchmark

```bash
# After fixing DashScope quota (disable "use free tier only" in console):
python -m src.eval.run_benchmark \
    --video data/videos/cooking.mp4 \
    --benchmark benchmarks/cn_video_qa_v2.json \
    --runs 3 \
    --methods agent,rag_only,vlm_direct \
    --output docs/benchmark_v2_results.md
```
