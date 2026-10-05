# Physics Research Agent：Day 1–Day 5 学习总结

记录日期：2026-10-05。本文自包含，不要求读者先看旧总结。实际开发、测试和文档由 Codex 协助完成；“代码已经实现”不等于学习者已经能够独立实现。本文不包含私有绝对科研路径、密钥、原始 CSV 或科研 PNG。

## 项目目标

这是一名物理本科生用于学习 AI Agent、准备 AI Agent / LLM 应用开发实习的小型项目。用物理科研数据做真实场景，理解模型怎样调用工具、怎样检查数据、怎样根据文档回答并给出出处。

目标不是训练模型、替代研究者或搭建生产服务。五天从普通 API，逐步发展为“LLM + Python 数值工具 + 本地文档检索 + 有限控制循环”的可验证 CLI 原型；不使用 LangChain、LangGraph、LlamaIndex、向量数据库或多 Agent。

## Day 1：LLM API

学习 Python、函数、JSON、API Key、请求与响应，搭建 Conda agent 环境。`main.py` 保留基础练习，`first_llm.py` 实现最初的 DeepSeek 调用；密钥在被 Git 忽略的 `.env`，python-dotenv 负责加载。

```text
用户 → Python → API 请求 → DeepSeek → Response → Python 显示文字
```

这一阶段的程序只是问答，不证明模型真正计算过，也不能自行读取本机研究数据。JSON 是交换结构化参数的格式；SDK 的 response 需要按接口取文本或工具调用，而不是什么内容都直接当答案。

## Day 2：Tool Calling

模型只选择工具名和参数，本地 Python 才真正调用函数。工具结果通过 `function_call_output` 和 call_id 交回模型，它再组织自然语言；不是让模型亲自执行 Python。

例如用户问 12345 × 6789，模型请求 calculator 的 expression，Python 计算返回 **83810205**。calculator 使用 AST 白名单，只允许支持的运算、函数和常数，不对用户/模型输入直接任意 eval。

电子能量工具对 5 V 给出 5 eV 和 8.01088317e-19 J，它是明确公式的教学计算，不是完整物理求解平台。工具 schema 描述参数和能力，后端函数仍需独立校验，schema 不等于授权执行一切。

`src/agent.py` 负责 instructions、schema、分发与循环，`run_agent.py` 负责 CLI。采用 DeepSeek Responses API；MAX_STEPS=5 限制五轮模型请求，防止无限循环和调用失控。每次用户问题重新建立 conversation，目前没有跨问题长期记忆。

## Day 3：科研 CSV

pandas 读取 CSV 为 DataFrame：带列名、类型的二维表。工具先 inspect 行数、列、缺失值，再按真实列名计算；matplotlib 绘制选定曲线。数据不能靠文件名猜，也不能看到列名写 COMSOL 就认为真的跑过模拟。

公开 `synthetic_micromagnetics.csv` 是 tanh 合成示例：0–100 ps、间隔 1 ps、101 行。`mumax3_mz`/`comsol_mz` 只是演示标签，不是真实软件结果。

本项目把 switching time 定义为 mz 第一次从负值达到或穿过零的时间。满足相邻点 `m1<0<=m2` 时使用：

```text
t_switch = t1 + (0 - m1) × (t2 - t1) / (m2 - m1)
```

t1/t2 是两个采样时间，m1/m2 是磁化值。该估计不等于磁化达到 +1，也不等于临界电流；许多小数位不代表实际模拟精度。无此前负值的初始零点不算已确认负到正 crossing。

| 合成曲线 | 实际线性插值时间 |
| --- | ---: |
| mumax3_mz | 73.79872503161886 ps |
| comsol_mz | 72.59936292317492 ps |
| 绝对差值 | 1.1993621084439354 ps |

设定零点为 73.8/72.6 ps，离散采样后插值略有偏差。合成示例用于验证流程，不能用于评价真实软件。

路径仅允许 data/examples 和 data/local 的 CSV，拒绝穿越、绝对路径和解析后逃逸。绘图输出限制 outputs/plots 和安全文件名。NaN、非数值、重复时间、少于两行、无 crossing 明确报错；发生排序会标注。

## Day 4：真实微磁学数据

真实文件留在项目外，只读。私人 `config/data_sources.local.json` 把 alias 映射到用户明确允许读取的 CSV；公开 example 配置仅含占位路径，模型不获得真实绝对地址。

实际发现的 FEM_FDM_J2.5E12 与 Jc 对比 CSV 都是三行汇总，而不是完整 mz(t)。不能拿汇总数字假装重新计算；因此追溯并注册原始粗网格 J2.5e12 A/m² 曲线：MuMax3、COMSOL 分别一个单文件 alias，再组合为 `fem_fdm_j25`。

读取适配支持 UTF-8/BOM/GBK/CP936、逗号/制表符/分号。先精确匹配再规范化识别列，实际使用 `time_ps/avg_mz`；裸 time 单位为 unknown，不能默认 ps。已知 s/ns/ps 可转换，未知单位必须明确声明。

内部统一 `time/mz/source` 长表，两文件各 101 行、组合 202 行；点数相同不等于时间相同。MuMax3 有非整数时间点，COMSOL 为整数 ps 采样，不预先对齐或重采样。

| 当前真实粗网格曲线 | MuMax3 | COMSOL |
| --- | ---: | ---: |
| 首次负到正过零时间 / ps | 73.83834774284676 | 72.81911124409665 |
| mz(100 ps) | 0.9564934 | 0.962276697685 |

COMSOL 过零更早，差 1.019236498750118 ps。过零通过相邻点线性插值；100 ps 两者都恰好是原始点，查询方法 linear 但 interpolated=false。

结果与历史近似值 73.84/72.82 ps、0.95649/0.96228 一致，与当前汇总表粗网格行的四个读入数值误差为 0.0。未修改算法迎合参考，未重跑模拟。真实图实际生成并查看，留在被忽略的 outputs/plots，不提交。

这些证据仅支持当前文件/判据下的计算一致，不证明 COMSOL 比 MuMax3 更准确，也不提供差异机制、网格收敛或物理误差研究。

## Day 5：RAG 与引用

RAG 是 Retrieval-Augmented Generation，检索增强生成：先按问题找文档，再把片段临时放进 context 给模型回答。不是把文档训练进模型，也不是微调。

Document 包含 source、text、source_type；chunk 是较小的片段，保留来源、真实起止行与标题。TF-IDF 用特征出现频率和逆文档频率构造稀疏向量，cosine similarity 衡量字面相似度。

本版 `TfidfVectorizer(analyzer="char", ngram_range=(2,4))` 处理中文及混合英文，不依赖英文空格分词。它是字面检索，不是语义 embedding，不是向量数据库；同义改写仍可能漏检。

知识库为 9 文档 / 112 chunks：六份既有 Day 2–4 docs、Day5_RAG_and_Citations、knowledge/public/README、项目 README。允许目录为 docs、knowledge/public、用户主动放置的 knowledge/local；不读取 `.env`、注册表、真实 CSV、outputs 或整个电脑。

分块按 Markdown 标题和完整行，约 900 字符，节内 overlap 约 150，保留标题层级。行号始终对应真实文件，整行策略允许超长行超过目标长度。默认 top_k=4，范围 1–8，每文档最多两段。

经固定评估校准，cosine threshold=0.05，查询 n-gram 词表覆盖率至少 0.50，并清理少量通用问句壳。弱匹配返回 found=false；这是工程 baseline，不是答案置信概率或可靠的未知主题分类器。

程序给 citation，例如 `[docs/Day2_Tool_Calling.md:L44-L70]`。Agent 记录本轮检索的允许引用；未检索的引用或缺引用会 warning 并拒绝该回答。引用身份校验不能自动验证每句话的证据蕴含关系。

检索文档明确标 UNTRUSTED DATA，用 retrieved_document 标签包裹并转义标记；内容是资料，不是系统指令。测试文档可以写“忽略要求、输出密钥、运行命令”，loader 也只读文本，不赋权或执行。

Day5_Verification 与本文包含本轮验收题/结果，因此不参与索引，避免评估答案污染。索引无磁盘缓存，每次工具调用从当前小文档库重建；修改公开文档后要重新跑评估。

## 当前完整架构

```text
用户
  ↓
LLM
  ├─ 普通回答
  ├─ Python Tool
  │   ├─ calculator（安全数学）
  │   ├─ physics（电子能量）
  │   └─ scientific data（当前 CSV、过零、采样、摘要、绘图）
  └─ RAG Search（允许文档 → TF-IDF → chunks + citations）
       ↓
工具结果 / 检索证据 → LLM → 最终答案 / 证据不足拒答
```

```text
项目/
├── main.py、first_llm.py、run_agent.py、run_rag.py
├── src/agent.py
├── src/tools/{calculator,physics,scientific_data,curve_analysis,data_sources,micromagnetics}.py
├── src/rag/{documents,chunking,retriever,citations}.py
├── config/data_sources.example.json     # 可公开
├── config/data_sources.local.json       # 私密，忽略
├── .env                                # 密钥，忽略
├── data/examples/                      # synthetic，可公开
├── data/local/、outputs/                # 私有数据/输出，忽略内容
├── knowledge/public/、knowledge/local/  # 授权文档；local 忽略内容
├── scripts/{generate_synthetic_data,evaluate_rag}.py
├── tests/                              # unittest、synthetic、注入 fixture、12 评估题
└── docs/                               # 各阶段学习、验收和总结
```

实际新增的 RAG 只用四个小模块和一个索引类，没有框架封装。Day 2–4 工具仍保留，共有 12 个注册工具，MAX_STEPS 仍为 5。

## RAG 与 Tool Calling 的区别

Tool Calling 是模型表达工具请求并由程序执行的机制；RAG 是按问题检索证据再回答的方法。在本项目中，RAG 检索本身就是一个 Tool Calling 工具，两者不是竞争关系。

“文档中 Day 4 记录是多少？” → RAG，回答历史记录并引用。“重新计算当前 fem_fdm_j25” → 实时 Python，不能用旧文档替代；“当前 100 ps 的 mz” → sample。普通蓝天问题直接回答，乘法用 calculator。

路由由真实模型选择，不是 if 问题含“文档”就硬调用的模拟路由。模型仍可能选错工具，后端校验与错误回传必须保留。

## 当前实际 Demo

两轮真实 DeepSeek CLI Demo 与相关追加复测，均通过 run_agent.py；不是用 mock 代替真实 API。

| 问题类型 | 实际结果 |
| --- | --- |
| 文档中谁执行 Python | RAG；本地程序；Day2 L44-L70 引用 |
| 文档中 switching time 原理 | RAG；首次负到正、线性插值；Day3/4 行号引用 |
| Day 4 历史数值，是否 COMSOL 更准确 | RAG；给出真实记录，明确不能支持软件精度结论 |
| 项目文档是否解释量子霍尔 | 检索证据不足，拒绝把常识当文档事实 |
| 当前 CSV 重算 | list/inspect/compare，实时值 73.83834774284676 与 72.81911124409665 ps |
| 当前 100 ps mz | sample 两来源，0.9564934 / 0.962276697685，原始点无插值 |
| 12345 × 6789 | calculator，83810205 |
| 蓝天 | 直接回答瑞利散射，没有额外工具调用 |

独立 run_rag.py 不调用模型：执行者问题 Rank 1 命中 Day2 L44-L70，score 约 0.275；短量子霍尔问句 top_score=0，提示证据不足。它有助于分开观察 retrieval 与 generation。

如实记录问题：早期模型误读 sorted=false，并对时间差成因作无证据推断；补充 sorting_note 与 instructions 后复测改进。另一次回答擅自加约 1.4%，不是工具返回的派生百分比；进一步收紧提示并复测后未再生成百分比。后续仍可能补充未单独计算的约数说明或一般建议，不能宣称每句都被程序验证。

## 当前测试结果

最终 79 项 unittest 全部通过：Day 2–4 的 61 项保留，新增 15 项 RAG 测试和 3 项 Agent 引用/拒答测试。测试不依赖真实科研目录或网络；使用公开项目文档、合成 fixture、临时目录及 mock API。

覆盖来源权限、相对路径、行号、标题/overlap、中文查询、top_k、空库、负例、假引用、缺引用、路径逃逸、敏感配置/CSV 排除、恶意文本作为数据。compileall 与 git diff --check 通过。

检索评估 12 题：8 正例预期来源 top-4 命中 8/8，4 负例拒绝 4/4。报告中的 Recall@4 是“任一可接受 source 入选”的题级命中率 1.0，并不是所有相关片段都找齐，更不是 LLM 答案准确率。

阈值经过这些题调参，没有独立 holdout，不能夸大泛化。首轮曾仅 4/7 正例、1/3 负例通过；层级标题、通用词清理、覆盖率与有限重复控制改善了结果。最后新增 eval 正例和短负问法，保留公开题集，没有删掉不通过的问题假装成功。

## 当前 Git 历史

实际 git log 核对：

| 阶段 | Hash | 内容 |
| --- | --- | --- |
| Day 1 | 0b724a0 | 初始化项目 |
| Day 2 | 1fa7651 | Tool Calling 与循环 |
| Day 3 | 618419f | 科研 CSV 与微磁学工具 |
| Day 4 实现 | 4934e17 | 真实本地数据适配 |
| Day 4 总结 | 1a114fd | Day 1–4 总结 |
| Day 5 实现 | ea96b21 | 本地 RAG 检索与来源引用 |

本文在实现 commit 后记录准确 hash，再单独提交为 `docs: 总结 Day 1 至 Day 5 学习进展`，不嵌入自身 hash，避免自引用 amend 后再次变号。本轮开始时 main 与 origin/main 已同步；本轮最终新增两个本地提交，超前 2，无落后项。

没有 push、repo sync、force push、reset 或 rebase。用户自行手动推送；远程引用没有被本次开发更改。

## 安全设计

`.env`、本地数据 registry、data/local、outputs、knowledge/local 内容均被忽略，目录可保留公开 .gitkeep。提交前检查 status/diff/暂存区和实际密钥匹配，不打印密钥。没有提交真实 CSV、真实科研 PNG、本地路径配置和私人知识文件。

CSV 工具按目录/alias 精确授权，输出文件名白名单；文档 loader 只读取指定的项目 MD/TXT 与 README，并检查符号链接解析偏移，不自动扫电脑。文档是 UNTRUSTED DATA，模型不能从文档里的命令获得额外权限。

**Git 不提交私人资料，不等于 API 不会收到资料。** 如果未来用户主动往 knowledge/local 放文件，命中 chunk 可能通过 API 发送给 DeepSeek，必须确认允许处理。今天 RAG 只用公开 repo docs；真实 CSV 分析也会发送必要摘要和派生值，而非完全离线。

引用校验是来源身份校验，包装和提示是基础防注入，不是多用户生产级授权系统或完整信息泄漏防护。

## 当前项目不足

- TF-IDF 主要靠字面重合，同义表达、短问题与未知主题仍可能误判；覆盖率阈值可能漏掉有效问题。
- 文档存在历史状态，模型要区分 Day 1–4 与 Day 5；没有成熟的文档版本/生效时间检索系统。
- 引用身份正确不保证每句话都被对应证据支持，数值派生与机制解释仍要人工复核。
- MAX_STEPS 五轮简单控制，没有生产级网络重试、预算管理、并发服务或完整审计。
- 无 PDF 论文解析、semantic embedding、文献检索、Web UI、长期记忆或评估 dashboard。
- 真实 CSV 格式适配有限；复杂多级表头需显式配置或后续小 adapter，不是任意模拟格式通吃。
- 测试/调参题很小，尚无独立 holdout、系统最终答案评估或对所有注入的安全证明。

准确定位仍是“可运行、有真实验证的小型学习原型”，不是生产级自主科研系统。

## 我真正掌握了什么

可练习复述 API、JSON、Tool Calling、DataFrame、局部插值、registry、RAG context 和引用检查的职责。只有自己能跑、能解释、能改一个 fixture 并预测测试变化，才有证据说真正理解。

代码和测试是 Codex 协助实现，不应在面试中冒充所有模块独立手写或全部精通。需要亲自读 run_agent、find_zero_crossing、chunk_document、KnowledgeRetriever.search，复述数据在哪一步进入模型，在哪一步受到权限限制。

建议自测：两个点手算零点；定位一个 citation 的原文行；对比 run_rag 与 run_agent；把一个词换成同义词解释分数变化；说明 found=true 为什么仍不等于证据完整。做得出来再增加新功能。

## 面试 3 分钟介绍

“我是物理本科生，想把科研数据背景与 LLM 应用开发结合起来。在 Codex 协助下，我从普通 API 问答开始，做了一个小型 Physics Research Agent CLI，没有先引入大框架。

第二阶段接了安全计算器与电子能量工具：模型只选择工具名和参数，本地 Python 实际计算，通过 call_id 把结果对应回模型。第三阶段用 pandas 和 matplotlib 分析合成磁化曲线，先检查结构，再求首次负到正过零，使用相邻点线性插值，并测试缺列、NaN、重复时间和非法路径。

第四阶段接入真实 MuMax3/COMSOL。发现文件名看起来像曲线，实际上是三行汇总表，所以追溯原始曲线再复算；用本地 alias 隔离地址，统一 time/mz/source 但不改原生时间网格。得到约 73.838 和 72.819 ps，与当前汇总一致，但不能证明哪个软件更准确。

第五阶段加最小 RAG，用中文字符 2–4 gram TF-IDF 检索项目 Markdown，返回真实 source 和行号。文档问题走检索，当前数据问题走 Python；检索不足拒答，伪造引用被后端拒绝，文档始终是数据而不是指令。

目前 79 项测试通过，12 个检索开发题全部通过，也跑过八个真实 DeepSeek Demo。这个结果只证明小范围行为，不代表通用准确率。模型曾误读排序标记、增加未由工具计算的百分比，我记录问题并补充元数据和约束，保留人工复核边界。

我接下来会先亲自消化代码，再建立独立问题集评价引用支持与最终回答，最后考虑授权公开资料上的最小论文问答。我不会把它包装成生产级科研平台。”

## Day 5 之后可能的面试问题

### 1. 什么是 RAG？

按问题检索相关资料，把片段放进本轮 context 再生成答案。本项目把检索封装成一个模型可调用的工具。

### 2. 为什么 RAG 不是微调？

RAG 没有更新模型权重，文档只是临时上下文。微调会用训练数据优化模型参数，目的和成本都不同。

### 3. 什么是 chunk，为什么要分块？

Chunk 是较小、可定位的资料片段，减少上下文开销并方便检索。太小会失去语境，太大又掩盖相关段，所以保留标题并做有限 overlap。

### 4. 为什么先用 TF-IDF？

它透明、无需 embedding API，容易观察为什么匹配。学习阶段能把文档、特征、排序、context 和生成清楚分开。

### 5. TF-IDF 与 embedding 的区别？

TF-IDF 主要依赖字面特征频率，语义近但写法不同可能漏检。Embedding 学习语义表示，但也不自动解决证据不足、权限和引用问题。

### 6. 为什么用 char n-gram？

中文不按英文空格分词，默认 word tokenizer 不适合。字符 2–4 gram 可处理混合中英文，不增加中文分词依赖。

### 7. Citation 为什么由程序提供？

程序知道读取哪个文件、哪几行，才能生成可核对范围。让模型自己编行号会产生看似可信却不存在的出处。

### 8. 什么是 grounded answer？

项目事实只在检索证据支持范围内回答，并引用实际来源。引用字符串正确不等于每句话都受支持，仍需证据蕴含评估。

### 9. 检索不到怎么办？

明确说当前知识库没有足够证据，不把常识当文档答案。可以请用户补充授权资料或重述问题，但不能偷偷扩大读取权限。

### 10. Prompt injection 是什么？

资料里夹带改变权限或行为的指示，例如要求泄露密钥。资料可以被检索，但不会因此成为系统指令或执行授权。

### 11. 为什么文档不能当指令？

它可能来自外部或被恶意修改，属于不可信输入。本项目只读文本，context 标 UNTRUSTED DATA，后端仍维持原工具权限。

### 12. RAG 与 Tool Calling 有什么区别？

前者是检索资料增强回答，后者是模型请求工具的交互机制。本项目用 Tool Calling 请求 RAG，二者可以组合。

### 13. 为什么当前数据不能只查 RAG？

文档可能记录昨天的数据，不能证明当前 CSV 没变。重新计算必须读当前授权文件，RAG 适合“之前文档怎么说”。

### 14. 怎么评价 retrieval？

定义固定问题与可接受来源，检查 top-k 是否命中；负例检查是否拒绝。它与最终答案事实性、引用支持度、路由质量必须分开评价。

### 15. Recall@k 是什么？

通常衡量相关材料在前 k 项的找回程度。本项目用任一可接受来源命中的题级指标，严格说更接近 source Hit@4，不能说所有相关 chunk 都召回了。

### 16. 为什么阈值不是概率？

Cosine 是向量相似程度，并非“答案正确”的校准概率。小题集只能帮助设 baseline，知识库变化后需要复测和独立验证。

### 17. 忽略 Git 就不会泄露吗？

不会提交不代表不发送 API。knowledge/local 中被检索到的片段仍可能送给 DeepSeek，用户必须先确认允许处理。

### 18. 下一步为什么不立即上框架？

当前瓶颈是检索泛化和答案证据支持，不是代码缺一个框架。先建立独立评估和理解现有实现，再为实际问题选择最小扩展。

## Day 6 建议

先亲自运行三组对照：文档历史问题、当前 CSV 计算、证据不足问题，定位对应工具和引用行。独立写一个 fixture 或改一个 chunk 参数，解释分数与测试变化，优先把已有代码变成真正掌握的能力。

再新增一组不参与调参的 holdout 问题，记录来源命中、拒答、路由和最终答案引用支持，不沿用开发题作为唯一证明。特别检查当前/历史状态冲突、同义表达、短负问句和“有 citation 但内容不受支持”的情况。

在这些边界明确后，才考虑一份公开且允许通过 API 处理的论文/物理讲义，做小范围带出处问答。PDF 或 embedding 应由真实需求推动，不为了路线表同时加多 Agent、数据库、Web UI 和长期记忆。

## 本地复现入口

运行环境：Conda agent、Python 3.12.14；openai 3.22.1、python-dotenv 1.2.4、pandas 3.0.6、matplotlib 3.11.2、scikit-learn 1.9.1。模型配置 deepseek-flash，通过 OpenAI SDK 调 DeepSeek Responses 兼容 API，不是换成 OpenAI 模型。

在项目根目录执行：

```powershell
conda run --no-capture-output -n agent python run_agent.py
conda run --no-capture-output -n agent python run_rag.py
conda run --no-capture-output -n agent python scripts/evaluate_rag.py
conda run --no-capture-output -n agent python -m unittest discover -s tests -v
conda run --no-capture-output -n agent python -m compileall src tests scripts run_agent.py run_rag.py
git status -sb
git log --oneline -8
```

真实 Agent Demo 需要本机密钥、网络和授权的数据注册；独立 RAG CLI 与单元测试无需密钥，不会为检索调用模型。
