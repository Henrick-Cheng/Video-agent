# Exact-Match 与生成式 Agent 的指标错配

> 一句话:**Exact-Match(EM)是为 AGQA 原生的封闭词表 / 判别式模型设计的;本项目是生成式 ReAct Agent,二者存在结构性错配。** 在 binary(yes/no)上 EM 可信;在 open / duration / sequencing(尤其 "X or Y" 选择题)上,EM 因答案抽取产生**双向误差**(假阳 + 假阴),只能作保守参考。

## 1. 为什么会错配

AGQA 的官方 EM 协议假设:模型直接输出**一个规范化的短答案 token**(yes / no / 物体名 / before·after),与金标准做字符级严格匹配。这套协议天然适配 AGQA 自带的**判别式 / 封闭词表**基线模型。

本项目的方法是**生成式多轮 ReAct Agent**:它先用工具检索时序场景图,再用自然语言**推理并叙述**地给出答案。这带来一个无法两全的困境:

- **不约束** → Agent 输出长篇推理("The scene graph shows … therefore …"),EM 无法直接匹配。
- **用 system prompt 强约束短答案** → 多轮 Agent 要么压垮工具调用(不检索、直接猜),要么仍在最终轮叙述(产品 prompt 的"引用证据"要求与之冲突)。
- **事后用 LLM 抽取短答案** → 抽取步骤本身在选择题上**不可靠**(见下方铁证)。

也就是说:把一个为"封闭词表单 token 模型"设计的指标,套到"生成式推理 Agent"上,中间必然要插一道**答案归一化 / 抽取**,而这道工序会引入它自己的误差。

## 2. 铁证(真实数据,来自 03PRW.mp4 冒烟跑)

> 评测集 `benchmarks/agqa_en_smoke.json`,原始记录见 `docs/archive/benchmark_en_smoke.json`。

**问题**(duration 类,"X or Y" 选择):
> *Was the person snuggling with a blanket or sitting in a bed for a shorter amount of time?*
> **gold = `sitting in a bed`**

**Agent 原始答案**(检索后推理):
> "The scene graph shows information about a person snuggling with a blanket (lying_on a pink blanket) but **doesn't show any instances of 'person sitting in a bed'**. … I don't see any triplet indicating the person sitting in a bed. **The person is shown sitting on a patterned couch** …"

→ Agent 的**实际结论是 couch / 没有 bed**(即它答错了,或认为前提不成立)。

**抽取出的短答案 = `sitting in a bed`**(恰好等于 gold)→ **EM = 1.0(假阳性)**
**LLM-judge = 0.0**(判对——Agent 确实没得出 "sitting in a bed")

**原因**:抽取器看到问题里 "X **or** Y" 两个候选,**挑了与 gold 一致的那个**,而非忠实复述 Agent 的结论。

**对照另一道 duration 题**(*eating food or watching television … shorter?*,gold = `watching television`):Agent 推理出"watching 几乎没发生 → 时间更短",抽取得 `watching television`,EM=1.0 且 LLM-judge=1.0(**这次抽对了**)。

> 两道同类题:一道抽取假阳、一道抽取正确 —— 抽取在选择题上近乎**掷硬币**。这不是可以靠调 prompt 修干净的 bug,而是"生成式输出 → 封闭词表 EM"这一步的本质噪声。

## 3. 分类结论

| 类别 | 占比(70 题) | EM 可信度 | 说明 |
|---|---|---|---|
| binary (yes/no) | 24 | ✅ 可信 | Agent 的 yes/no 抽取干净、匹配明确 |
| open | 21 | ⚠️ 含噪 | 物体名抽取可能假阴(同义/近义)或假阳 |
| sequencing | 14 | ⚠️ 含噪 | 顺序/对象抽取受叙述影响 |
| duration | 11 | ⚠️ 含噪 | "X or Y" 选择题,抽取易挑中 gold 选项 → 假阳 |

LLM-judge 对**所有类别**的生成式输出都更公平(它读完整答案、按语义判分),代价是它本身不是 AGQA 官方协议、且(若用 Qwen 判 Qwen)有自偏好混杂——后者可通过把 judge 换成 GPT 缓解(代码已支持 `JUDGE_BASE_URL/JUDGE_MODEL` 配置切换)。（后记 2026-07-17：MMBench-Video 线上已做 gpt-4-turbo 全量重判交叉验证，总分差 <0.015、逐题一致率 0.76–0.81——自偏好在该设置下被实证为不成立。）

## 4. 建议口径

1. **LLM-judge 作主指标**:对生成式 Agent 公平,反映真实能力;作简历/主线结论。
2. **EM 作"对标 AGQA 协议"的保守下界**:全程**披露**抽取局限;**binary 上的 EM 当真**,其余类别的 EM 标注"含抽取噪声,仅供参考"。
3. **两列并报**,让"宽松指标下的优势"与"严格指标下还剩多少"都可见——这个 gap 本身是论文看点。

## 5. 给博士后的一句话

> EM 对生成式 Agent 在 open/选择类上会因答案抽取产生假阳/假阴(binary 可信)。是否接受**"EM 作保守下界 + LLM-judge 作主指标 + 全程披露抽取局限"**这一口径?若坚持纯 EM,则需要么把 Agent 强制约束为"只输出封闭词表选项"(多轮推理 Agent 难以稳定压住),要么承认"生成式方法 × 封闭词表指标"不完全兼容。

---

*附:本结论由英文管线迁移后的冒烟评测得出。完整逐题记录(原始答案 → 抽取短答案 → 双评分)见 `docs/archive/benchmark_en_smoke.json`;评测器实现见 `src/eval/run_benchmark.py`(`_judge_exact` / `_extract_short_answer`)。*
