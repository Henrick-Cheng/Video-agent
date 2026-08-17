# 论文 LaTeX(会议版 + 学位版):Method 章 + Evaluation/Experiments 章

本目录包含两套可编译的 LaTeX 工程。Method 章是把 `docs/thesis/ch4_method.md` **仅做格式转换**
得到的(原 markdown 原样保留);Evaluation/Experiments 章是**新撰写**的(学位版按
`docs/reviews/thesis_outline.md` 的 Ch.5 规划,会议版按 `docs/reviews/paper_outline_cvpr.md`
的会议大纲),数字全部取自仓库权威结果文档并经脚本审计对源。

**两版都已在本地编译通过**:会议版 9 页、学位版 23 页,0 处未定义引用(除第 3 章占位),
0 处未定义文献,参考文献 11 条正常渲染,学位版 0 处 overfull box、会议版仅剩 1 处 1.4pt
(肉眼不可见)。

```
latex/
├── Makefile                 # make / make conf / make diss / make watch-conf / make warnings
├── .gitignore               # 编译产物不入库
├── conference/     # CVPR 2026 会议版(article 类、双栏)—— 自包含,可直接 Upload Project
│   ├── main.tex             # 结构与官方 author kit 一致
│   ├── preamble.tex         # 官方 preamble 原文 + 本文所需的额外宏包(分隔线以下)
│   ├── cvpr.sty             # 官方文件(CVPR2026-v1(latex) release,未修改)
│   ├── ieeenat_fullname.bst # 官方文件(同上,未修改)
│   ├── sec/method.tex       # Method(Ch.4 逐字格式转换)
│   ├── sec/experiments.tex  # Experiments(按会议大纲新写,定义 \label{sec:eval})
│   ├── refs.bib             # 11 条文献(5 条 Method + 6 条评测,均已联网核实)
│   └── fig/                 # ch4_architecture.{svg,pdf} + frame_scaling.{svg,pdf}
└── dissertation/   # 学位论文版(report 类、单栏,Chapter 4/5 编号)
    ├── main.tex             # 自包含骨架(含 \appendix)
    ├── sec/method.tex       # Chapter 4 Method
    ├── sec/evaluation.tex   # Chapter 5 Evaluation(5.1–5.9 全量,定义 \label{ch:eval})
    ├── sec/appendix.tex     # 附录:全 150 口径 frame-scaling 表 + L2 全表(±std,双口径)
    ├── refs.bib
    └── fig/
```

**同步规则(重要)**:
- 两个 `sec/method.tex` **正文逐字相同**,改动要同步(排版参数如列宽/字号可以不同)。
- Evaluation(学位版)与 Experiments(会议版)**文风刻意不同**(学位版 9 小节全量叙述;
  会议版紧凑、AGQA/标注审计只留短段指向 supplementary)——**文字不同步,但数字必须一致**;
  改任何数字时两份都要改,并跑一遍数字审计(见 §四点五)。

---

## 零、本地编译(推荐:不再受 Overleaf 免费额度/超时限制)

本机已装好完整工具链,**在本目录直接 `make` 即可**:

```bash
cd docs/thesis/latex
make            # 编译两版 -> conference/main.pdf, dissertation/main.pdf
make conf       # 只编会议版
make diss       # 只编学位版
make watch-conf # 持续编译:存盘即重编(Ctrl-C 退出)
make warnings   # 列出未定义引用/文献 + overfull box
make clean      # 清理中间文件(保留 PDF)
```

**已安装的东西**(以后换机器要重来一遍):

```bash
brew install texlive     # 完整 TeX Live 2026,不需要 sudo(与 MacTeX 的 .pkg 装法不同)
brew install librsvg     # 提供 rsvg-convert,用于 SVG -> PDF
```

TeX Live 由 Homebrew 装在 `/opt/homebrew/opt/texlive/bin`,**默认不进 PATH**。Makefile 里写了
绝对路径所以 `make` 随处可用;想在终端直接敲 `pdflatex`,把这行加进 `~/.zshrc`:

```bash
export PATH="/opt/homebrew/opt/texlive/bin:$PATH"
```

**在 VS Code 里写**:装 **LaTeX Workshop** 扩展(id `James-Yu.latex-workshop`)即可,配置已就绪:

- 仓库根目录的 [`.vscode/settings.json`](../../../.vscode/settings.json) 里已写好 latexmk 的绝对
  路径与子进程 PATH(Homebrew 版 TeX Live 不在 PATH 上,不配这条扩展会报"找不到 latexmk"),
  并开了**存盘自动编译**、PDF 在标签页预览、SyncTeX 双向跳转。
- 每个 `sec/*.tex` 顶部加了一行 `% !TEX root = ../main.tex`,所以**在任意小节文件里按编译,
  编的都是所属工程的 main.tex**(不会误把小节当独立文档编)。

常用操作:`Cmd+Alt+V` 开 PDF 预览;在正文里 `Cmd+Alt+J` 跳到 PDF 对应位置;在 PDF 里
`Cmd+点击` 跳回源码行。

**Overleaf 还留着做什么**:投稿系统对接、给师兄/导师看和批注、多人协作、最终稿留档。
平时改稿在本地,阶段性同步一次到 Overleaf 就够了——这样免费额度基本用不完。

---

## 一、会议版(CVPR 2026)在 Overleaf 上怎么用

`conference/` 现在**自包含**(官方 `cvpr.sty` 与 `ieeenat_fullname.bst` 已放进目录),
不必再从模板新建项目:

1. Overleaf → **New Project → Upload Project**,传 `conference.zip`。
2. 编译器保持 **pdfLaTeX**,**Recompile** 即可。
3. 若参考文献列表为空或正文出现 `[?]`:点 **Recompile from scratch**(逼 BibTeX 重跑)。
   注意官方模板自带的 main.tex 写的是 `\bibliography{main}`,本工程用的是 `refs.bib`,
   `main.tex` 里已相应写成 `\bibliography{refs}`——**别把两者混用**,这正是之前 `[?]` 的成因。

> `cvpr.sty` / `ieeenat_fullname.bst` 取自官方 author kit 的 `CVPR2026-v1(latex)` release
> (github.com/cvpr-org/author-kit),**未做任何修改**。投稿前建议核对一次官方是否发了新版。

### 审稿行号的位置修正(对官方 kit 的唯一偏离,写在 `preamble.tex` 末尾)

`cvpr.sty` 用 `lineno` 的 `switch` 选项,靠"当前在第几栏"决定行号放左还是放右。本文是双栏
且有跨栏浮动体(`figure*` / `table*`),该判断在这里判反了,**两栏的行号一起挤进 22pt 的中缝**;
再加上 kit 设的 `\linenumbersep` = 0.75cm(21pt)与三位数字的 13pt 宽度,每个行号都压进隔壁栏
正文——实测 9 页共约 500 处重叠。修正:

```latex
\makeatletter
\@ifpackageloaded{lineno}{\switchlinenumbers*\setlength{\linenumbersep}{8pt}}{}
\makeatother
```

`\switchlinenumbers*` 把左右判断翻回来(行号回到页面**外**边距);8pt 间距是保险——第 1 页因
`\twocolumn[\maketitle]` 打乱栏序仍会判成"内侧",8pt 能让行号完整落在中缝里而不碰正文。
**只改行号位置,不改编号本身**;`\@ifpackageloaded` 保证切到 camera-ready(不加 `[review]`,
不载入 lineno)时这段自动失效。核验方法:

```bash
pdftotext -bbox conference/main.pdf - | grep -o 'xMin="[0-9.]*"'   # 行号应聚在 x≈37 与 x≈558
```

## 二、学位版在 Overleaf 上怎么用

学位版**自包含**,不依赖任何外部样式文件:

1. Overleaf → New Project → **Upload Project**,传 `dissertation.zip`。
2. 编译器保持 **pdfLaTeX**,**Recompile** 即可。
3. `main.tex` 里 `\setcounter{chapter}{3}` 让 Method 显示为 **Chapter 4**;等你写好前 3 章后,把这行
   删掉、换成真正的 `\input` 前置章节。

---

## 三、变动清单(诚实记录:哪些不是"纯文字照搬")

**正文句子一律未改**(尤其诚实性红线:instructed budget vs enforced cap、difflib **0.85**、
L0 摘要 **8** 帧、qwen-vl-plus 等,数值全部原样)。以下是格式/结构层面不可避免的调整:

### 两版共同
- **中文 HTML 注释**:原文里的中文写作注释,只把"诚实性红线"那几条转成 `%` LaTeX 注释保留在
  `method.tex` 顶部,其余剥离(本就是渲染不可见的写作笔记)。
- **删除内嵌 mermaid 草图**:原文 4.1.3 里那段 ```mermaid``` 流程图删掉了。原文已注明"终稿以
  SVG 为准",但删除仍属内容删减,在此明确告知。正式架构图用 `fig/ch4_architecture`。
- **图/表/算法编号交给 LaTeX 自动生成**:原 markdown 手写的 "Figure 4.1 / Table 4.1–4.3 /
  Algorithm 4.1" 改为 `\caption`+`\label`,正文引用改 `\cref`。文字本身没删,只是编号方式变了。
- **markdown 语法 → LaTeX**:`**粗体**`→`\textbf`、`*斜体*`→`\emph`、`` `代码` ``→`\texttt`、
  管道表 → `booktabs` 表、`$$…$$` → `equation` 环境、伪代码 → `algorithmicx` 重排(逻辑与注释
  文字逐字对应)、直引号 `"…"` → LaTeX 的 ``` ``…'' ```、破折号 `—` → `---`。
- **插图改用预转 PDF**:`\includesvg[inkscapelatex=false]{...}` → `\includegraphics{...}`,
  图片由 `rsvg-convert -f pdf` 从同名 SVG 生成(见 §五)。**只是引图机制变了,图本身没变**;
  原 `\includesvg` 写法作为注释保留在原处,随时可切回。
- **排版参数微调以消除 overfull box**:个别表格改 `\small`→`\footnotesize`、调 `\tabcolsep`、
  微调 `p{}` 列宽;学位版另加 `\emergencystretch=3em`。**单元格文字与数字一个都没动**。

### 只发生在会议版
- **章标题**:`Chapter 4 — Method: Lazy Three-Layer Memory and Confidence-Driven Orchestration`
  → `\section{Method: Lazy Three-Layer Memory and Confidence-Driven Orchestration}`。去掉了
  "Chapter 4 —" 前缀(会议论文无"章"概念),**副标题文字原样保留、未丢内容**。
- **带编号的跨章引用措辞变了**:`Chapter 3` / `Ch. 3` / `Ch. 5` → `\cref{sec:diagnosis}` /
  `\cref{sec:eval}`,渲染成 **"Sec. N"**(会议论文里没有 Chapter;`Sec.` 是 cvpr.sty 定的缩写)。
  这是措辞变动,已逐处替换。泛指性的 `this chapter`(非编号引用)**未改**。
- **表格排版**:`Tool contracts`(5 列)用 `table*` 跨双栏、其余表加 `\small`/`\footnotesize`;
  **只改排版尺寸,单元格文字未动**。
- **main.tex 结构对齐官方 kit**:改为 `\input{preamble}` + `cvprblue` 版 hyperref 设置,与
  `CVPR2026-v1(latex)` 官方 main.tex 一致,便于日后 diff 新版模板。

### 只发生在学位版
- **基本零改动**:保留 `Chapter 4 / 4.1 / 4.2` 编号;跨章引用 `Chapter 3` / `Ch. 5` →
  `\cref{ch:diagnosis}` / `\cref{ch:eval}`,渲染**仍是 "Chapter N",措辞不变**。

---

## 四、占位交叉引用(编译出现 `??` 属正常)

Method 现在只剩**一个**未定义 label(评测章已补上,`ch:eval`/`sec:eval` 已解析):

| 会议版 label | 学位版 label | 指向 |
|---|---|---|
| `sec:diagnosis` | `ch:diagnosis` | 第 3 章(baseline 与诊断) |

写好该章并在那里放 `\label` 后,`??` 自动消失。`make warnings` 可随时确认还剩几处。

---

## 四点五、评测章(Evaluation / Experiments)说明

**来源与口径**(数字严禁凭记忆改;全部出处见各 tex 文件头部注释):
- 学位版 `sec/evaluation.tex` = Chapter 5,按 `docs/reviews/thesis_outline.md` 5.1–5.9 全量;
  附录表在 `sec/appendix.tex`(对应大纲 Appendix D)。
- 会议版 `sec/experiments.tex` = §Experiments,按 `docs/reviews/paper_outline_cvpr.md` §3;
  AGQA/标注审计/全 150 口径只留短段或脚注,细节标注 "see supplementary material"
  (supplementary 文件本身尚未产出,清单见会议大纲 §4)。
- 判分口径纪律:论文级/维度级 = gpt-4-turbo;抗噪 ±std = qwen-max runs=3;时长桶/归因派生 =
  qwen 原始分(正文已逐处标注)。帧数 3.6(runs=3);成本如实 2.1×;TR 输如实披露。

**数字审计**:改动任何评测数字后,重跑数字审计脚本(内置权威数字清单 + 禁词检查,
会议/学位两版分别核对)。脚本在会话 scratchpad(`check_eval.py`),或按其思路重建。
最近一次结果:两版全部通过(学位 81 项、会议 67 项数字在位;引用全解析;无违禁表述)。

---

## 五、插图:SVG 与预转 PDF

正文引的是 `fig/*.pdf`,由同目录的 `fig/*.svg` 用 `rsvg-convert` 预转而来;
`make figs`(或 `make`)会在 SVG 更新时自动重转。

**为什么不直接 `\includesvg`**:`svg` 宏包每次编译都要唤起 Inkscape 转图,是这两个工程里最慢
的一步,在 Overleaf 上也最容易吃满编译超时;而且本地/别的环境没装 Inkscape 就编不了。
预转 PDF 一劳永逸,矢量质量不变。

**如果要切回 SVG**:每个图的 `\includegraphics` 上方都留着注释版的
`\includesvg[inkscapelatex=false,...]{...}`,取消注释、并把 `\usepackage{svg}` 打开即可
(会议版在 `preamble.tex` 里,学位版在 `main.tex` 里)。
**`inkscapelatex=false` 不能省**:不加时 Inkscape 会把图里的文字抽出来交给 LaTeX 重排,而这两
张图文字密集、含下标/圈码/希腊字母且按精确坐标定位,重排后会错位重叠、缺字(即"一片混乱")。

**本轮对 SVG 本身的一处修改**:`frame_scaling.svg` 画布由 `580×712` 改为 `600×712`
(同时改了源文件 `docs/analysis/frame_scaling.svg`)——原宽度会把图例最后一项
"vlm\_direct (dense frames)" 的尾巴裁掉。**只动了画布宽度,曲线与数字未动**。
