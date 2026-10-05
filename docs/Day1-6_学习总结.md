# Physics Research Agent：Day 1–Day 6 学习总结

记录日期：2026-10-05。本文自包含，供 ChatGPT 审核及学习复盘。开发、测试和文档由 Codex 协助实现；代码完成不等于学习者已能独立实现。本文不包含密钥、私有绝对路径、原始真实 CSV/PNG 或私人论文。

## 项目目标

面向物理本科生的 AI Agent / LLM 应用开发学习与求职展示项目：让模型能调用受限 Python 工具，分析科研曲线，从本地文档和公开论文找证据，再形成可核对来源的中文回答。

不是训练模型、自动证明科研结论或生产级自主科研平台。六天采用小型可运行 CLI，保留真实测试和失败案例，没有引入 LangChain、LangGraph、LlamaIndex、向量数据库、多 Agent、长期记忆或 Web UI。

## Day 1：LLM API

理解 Python 函数、JSON、API 请求/响应与 API Key。`main.py` 是基础练习，`first_llm.py` 是最初问答；python-dotenv 从 Git 忽略的 `.env` 加载密钥。用户 → Python → DeepSeek API → 文本响应 → Python 显示。

普通 API 问答不等于模型真正执行了计算，也不能自然读取本机文件。当前环境是 Conda agent、Python 3.12.14；PowerShell activate 曾仍指向 base 3.8，因此运行时实际检查解释器，统一使用 conda run。OpenAI SDK 只作为调用 DeepSeek 的客户端，不意味着换成 OpenAI 模型。

## Day 2：Tool Calling

LLM 输出工具名与 JSON 参数，本地 Python 才真正执行函数。tool schema 描述能力和参数，TOOL_FUNCTIONS 做分发，后端仍校验输入；function_call_output 用 call_id 对应回模型，再由模型组织回答。

例子：模型请求 calculator 的 expression=`12345 * 6789`，Python 返回 83810205，模型再给自然语言结果。calculator 使用 AST 白名单，不对任意输入 eval。电子能量工具对 5 V 给出 5 eV 与 8.01088317e-19 J，是明确公式计算，不是完整物理求解器。

Agent Loop 限制 MAX_STEPS=5，即最多五次模型请求，而不是最多五次工具执行。一轮可提出多个请求，本地逐个执行。每个用户问题新建 conversation，没有跨问题记忆；工具错误作为结果回传，不替模型编数据。`src/agent.py` 管理循环，`run_agent.py` 提供交互。

## Day 3：科研 CSV

pandas 读取 CSV 为 DataFrame，先检查列、类型、缺失值和少量预览，再选择列分析；matplotlib 绘图。公开 synthetic_micromagnetics.csv 是自写 tanh 演示：0–100 ps，1 ps 间隔，101 行；软件名列标签不代表真的执行过模拟。

本项目定义 switching time 为 mz 第一次从负值达到或穿过零的时间，对 `m1<0<=m2` 的相邻点使用：

```text
t_switch = t1 + (0 - m1) × (t2 - t1) / (m2 - m1)
```

t1/t2 是采样时间，m1/m2 是对应磁化。过零不是磁化达到 +1，更不是临界电流。没有前一负值的初始零点不算确认 crossing。小数位多不等于物理精度高。

合成曲线插值时间分别为 73.79872503161886 ps、72.59936292317492 ps，差 1.1993621084439354 ps；设定零点为 73.8/72.6 ps，离散采样后略有偏差，不能用来评价真实软件。

工具拒绝缺列、NaN、非数值、重复时间、无 crossing、少于两点；未排序会排序并标记。CSV 只允许 data/examples 与 data/local 内文件，输出只写 outputs/plots，禁止路径穿越、外部任意路径与不安全输出名。

## Day 4：真实微磁学数据

真实科研文件留在项目外，只读。本地 config/data_sources.local.json 把用户授权的文件映射为 alias；公开 example 只有占位配置，模型不获得真实绝对路径。

发现名为对比 CSV 的文件实际上是三行汇总，不是完整 mz(t)，因此追溯原始粗网格 J2.5e12 A/m² 曲线，而非拿汇总数值假装重算。MuMax3 与 COMSOL 各注册单文件 alias，组合为 fem_fdm_j25。

适配 UTF-8/BOM/GBK/CP936、逗号/制表符/分号；列先精确再规范化匹配，歧义要求指定。时间单位支持 s/ns/ps，unknown 不猜为 ps。两曲线统一 time/mz/source，但不预先对齐时间点或重采样；各 101 行、组合 202 行，点数一样不表示时间一样。

| 真实粗网格固定电流曲线 | MuMax3 | COMSOL |
| --- | ---: | ---: |
| 首次负到正过零 / ps | 73.83834774284676 | 72.81911124409665 |
| mz(100 ps)，Day 4 已验证 | 0.9564934 | 0.962276697685 |

COMSOL 过零更早，差 1.019236498750118 ps。Day 6 实际重新计算 switching time 得到相同数值；100 ps 一行是 Day 4 已验证记录，不声称 Day 6 又做过这一查询。采样工具支持 nearest/linear，禁止外推；摘要返回初末值、极值和 crossing 数。

Day 4 数值与当前汇总粗网格行一致，未修改算法迎合参考、未重跑软件。只能支持该文件和判据下计算一致，不能证明谁更准确或约 1 ps 差异的机制，也没有网格收敛研究。

## Day 5：Markdown RAG

RAG 是 Retrieval-Augmented Generation：按问题找相关片段，把证据临时加入本轮 context，再让模型回答。它不是把文件训练进模型，不更新权重。

Document 是带来源的文本；chunk 是小片段。Markdown 按标题层级与完整行分块，目标约 900 字符、节内重叠约 150；超长完整行可超过目标。citation 由程序按实际 source 和 1-based 行范围生成，而不是让模型猜行号。

同一个 KnowledgeRetriever 使用 TfidfVectorizer(analyzer="char", ngram_range=(2,4))、cosine similarity；不需要中文分词和 embedding API。TF-IDF 的逆文档频率降低普遍特征的权重，但整体仍偏字面，不懂所有同义表达或跨语言语义。

默认 Top-K=4，允许 1–8，文本每来源最多两段；threshold=0.05，query n-gram 词表覆盖率>=0.50，清理少量通用问句壳。这是小评估集校准的工程基线，不是答案正确概率。

Day 5 快照是 9 份文档、112 chunks，79 项 unittest 通过，8 个正例来源命中与 4 个负例拒绝全部通过。Day 6 加入新内容后数量和排序会变化，不能把旧快照当当前状态。

检索允许 docs、knowledge/public、用户主动授权的 knowledge/local MD/TXT 与 README；不扫描整机，不读取 .env、registry、CSV 或 outputs。检索资料始终是 UNTRUSTED DATA，用标签包裹、转义。run_rag.py 只做检索，run_agent.py 才调用模型生成。

## Day 6：PDF 论文 RAG

新增 PyMuPDF==1.28.2，读取真正公开论文《The design and verification of Mumax3》，arXiv:1406.7635v3，2014。该版本作者为 Arne Vansteenkiste、Jonathan Leliaert、Mykola Dvornik、Felipe Garcia-Sanchez、Bartel Van Waeyenberge；不混用期刊版作者列表。

固定来源：https://arxiv.org/pdf/1406.7635v3 。最终下载通过 arXiv 最新 PDF 入口完成，本地第一页确认 v3 日期；正常 TLS，未关证书校验。只确认公开可访问，sources.json 记录 `publicly accessible source; license not verified`，不伪造 CC、不将软件 GPL 当论文许可。第三方 PDF 本体默认不提交 Git，克隆后需自行下载指定一份，没有自动下载器。

PDF 是固定版面，不是简单顺序字符串；文字、图像、位置分开存储。`pymupdf.open` 得到 document，每个 page object 可 get_text("text")。读取文字层不是 OCR；扫描图像可能无文字。当前不足 20 字符的页保守标记 empty_or_scanned，不猜 OCR 内容。

每页保留 source、paper_id、title、page_number=index+1、text、source_type="pdf"、提取状态。只轻量处理空白，不改公式与数字、不复杂删除页眉。32 页全部可提取，共 64,767 字符、104 PDF chunks。已查看渲染的 p2/p12，并实际读取评估涉及的页面。公式仍会断行、字形有连字，不能宣称完整数学解析。

只读 knowledge/public/papers 与 knowledge/local/papers 的直接 PDF。Path.resolve 拒绝穿越、外部绝对路径、UNC、符号链接偏移；模型只传 paper_id。list_knowledge_papers 列表显示元数据和 local_available；inspect_paper 给页数、可提取页数、字符统计和短预览，不回全文。

PDF chunk 复用完整行聚合，但每页独立，不跨页。程序生成 `[paper:mumax3:p12]`，页码为阅读器从 1 开始的物理页序，不伪造排版稳定行号。论文原文的 RK32/RK23 命名不一致保留不改；方法说明仅属于这份 2014 v3，不作为当前软件版本规范。

PDF 与文本同一个 TF-IDF baseline；scope=project_docs/papers/all，论文范围还可 paper_id 限定。英文论文优先英文关键词，模型可翻译检索词，但不是新 embedding 算法；中文直检英文论文实际出现漏检。

新增 run_pdf_rag.py、inspect_pdf.py、evaluate_pdf_rag.py。run_pdf_rag 不用 DeepSeek，方便观察 rank、page、score 与 excerpt。当前共有 14 个工具，MAX_STEPS 仍为 5。

## 当前完整架构

```text
                         用户
                          ↓
                         LLM
          ┌───────────────┼─────────────────┐
          ↓               ↓                 ↓
       普通回答       Python Tools        RAG Tool
                          ↓                 ↓
                     当前授权 CSV       同一个 TF-IDF
                                        ┌───┴────┐
                                        ↓        ↓
                                   Markdown     PDF
                                   项目历史    论文页面
                                        ↓        ↓
                                    行号引用   页码引用
          └───────────────┬─────────────────┘
                          ↓
              工具结果 + 证据 → LLM → 最终回答
                          ↓
                 本轮 citation 身份校验
```

核心代码：src/agent.py、src/tools、src/rag/{documents,pdf_documents,chunking,retriever,citations}.py；CLI：run_agent.py、run_rag.py、run_pdf_rag.py。每次 search 重建小索引，无持久数据库；scope 隔离是在同一检索器中选择输入资料，不是另写两套系统。

当前 11 份 Markdown/TXT + 32 个 PDF 页面，共 43 个索引 documents、243 chunks。按来源文件算是 12 个，论文只有 1 篇。验收记录 Day5/6_Verification 与 Day1-5/6 总结不进入索引，避免评估答案污染。

## 当前三类知识来源

| 来源 | 使用场景 | 依据 |
| --- | --- | --- |
| current data | 重新算当前 fem_fdm_j25 | Python 读取授权原始曲线，数值/单位/方法 |
| project docs | 项目历史、实现与学习记录 | Markdown 真实行号 |
| paper evidence | 根据论文说明数值方法 | PDF 实际页码 |

论文的一般方法不能代替当前数值重算；历史数值不能证明当前文件未变；当前两条曲线差异不能自动推出精度排名或物理机制。综合问题分别给两类来源，证据不够明确说不足以归因。

## PDF RAG 数据流

用户问论文 → LLM 发检索词与 papers scope → Python 从允许目录逐页提取 → 页内 chunk → TF-IDF 排序 → Top-K 证据/context/citation → LLM 中文概括 → Python 校验本轮引用。

论文问题可先 list/inspect，模型不能随意扩大目录授权。sources.json 记录论文身份、标题、作者、年份、公开 URL、访问说明、文件名；未下载的已登记论文可显示 local_available=false。缺文件不当成空论文成功，也不靠私人文件 fallback。

## Citation 设计

Markdown 示例 `[docs/Day2_Tool_Calling.md:L44-L70]`；PDF 示例 `[paper:mumax3:p12]`。Agent 每轮问题收集实际返回的允许集合，fake:p99、未返回来源或缺引用会 warning 并拒绝回答。

校验确保 citation identity，即引用字符串来自真实检索；不是 claim entailment，即每个主张是否由证据蕴含。found=true 也不保证证据完整。引用页码正确但内容不支持，仍是错误回答；需要人工核对与独立最终回答评估。

PDF/TXT 都是不可信数据，不能因文本出现“忽略指令、泄露密钥、执行命令”而获得权限。标签与转义是基础防护，不是完整安全证明。

## 当前实际 Demo

Day 6 实际运行 run_agent.py，与 DeepSeek 真实交互，未拿 mock 充数：

1. 论文列表 → list_knowledge_papers，返回唯一 mumax3。
2. 基本信息 → inspect_paper，32/32 可提取、0 空页。
3. 空间离散与物理量位置 → papers 检索，FD/正交单元、中心与面，引用 p2。
4. 默认时间积分 → papers 检索，RK45 Dormand–Prince，引用 p12。
5. GPT-6/量子霍尔标准负例 → papers 检索，拒绝编数值；初版过强断言全文没有，加强提示后复测说明当前片段不足，不能推断全文。
6. Tool Calling 谁执行 Python → project_docs 检索，引用 Day2 L44-L70。
7. 当前 fem_fdm_j25 → list/inspect/compare，约 73.838/72.819 ps，不走 RAG。
8. 12345×6789 → calculator，83810205。
9. 天空为何蓝 → 普通 LLM，无工具；只确认路由，未将每条扩展科普作为经过严格科学审核的结论。

综合问题实际同时使用 PDF RAG 和当前科研工具：默认 RK45/p12 + 两条原始曲线过零时间/alias。初次 8 个工具执行、最终提示下复测 5 个工具执行，均在最多五轮模型请求内完成，未提高 MAX_STEPS，也不据一般论文归因约 1 ps 差异。真实工具调用顺序由模型决定，重复运行可能不同。

额外歌剧问题虽拒绝编造论文剧情，首句仍有“论文没有”的过强措辞，后文补充 Top-K 限制；保留为尚存的生成风险，不宣称提示已经根治此类问题。

## 测试情况

105/105 unittest 通过，原 Day 2–5 的 79 项保留，新增 PDF 22 项与 Agent 4 项。覆盖目录授权、穿越/UNC/链接偏移、损坏文件、页码、空页、页内 chunk/overlap、中英文提取检索、注入转义、伪造页码、scope、ignore 和非法 JSON 参数。

自产 fixture 由 PyMuPDF 动态生成四页：自写中英文 Tool Calling、插值说明、恶意文本、空白页。测试不下载论文，不调用真实 API，不依赖真实科研目录；真实论文和 DeepSeek 单独用于 integration Demo。

compileall src tests scripts run_agent.py run_rag.py run_pdf_rag.py、git diff --check 均通过。PDF 本体 check-ignore 通过，私有目录只 tracked .gitkeep；暂存区实际密钥匹配检查为 0，没有新增真实 CSV/PNG 或用户绝对路径。

## Evaluation

必须区分检索页/来源命中、负例检索拒绝、生成回答质量与 citation 支持，不能统称 LLM accuracy。

| 评估 | 正例 | 负例 | 说明 |
| --- | --- | --- | --- |
| Day 5 原文本基线，9/112 | 8/8 | 4/4 | 修改前实际复核 |
| Day 6 project_docs，11/139 | 8/8 | 4/4 | 项目范围没有漏掉旧 expected source |
| Day 6 all，43/243 | 7/8 | 4/4 | Day4 历史数值的指定来源被挤出 Top-4 |
| PDF 固定 6 正例＋2 负例 | 6/6 页命中 | 1/2 拒绝 | 英文歌剧负例误召回 |

PDF 六题来自实读页：FD/p2、OVF/p3、FFT/p4、RK45/p12、Relax/p13、标准问题4/p15–16。英文歌剧负例 score约0.167、coverage约0.803，显示通用英文 n-gram 误匹配；中文直问数值方法 coverage约0.222，显示跨语言限制。两项失败评估脚本诚实退出 1，没有删题凑全通过。

通过 scope 分流让项目文档继续 12/12，但联合库排序仍真实有退化。开发题很小，包含提示性关键词，不能代表独立泛化、最终答案事实性或注入安全率。模型拒绝编造负例内容不等于检索器拒绝率提高。

## Git 历史

| commit | 阶段 |
| --- | --- |
| 0b724a0 | 初始化 Physics Research Agent |
| 1fa7651 | Tool Calling 与基础 Agent 循环 |
| 618419f | 科研 CSV 与微磁学数据工具 |
| 4934e17 | 本地真实微磁学数据分析 |
| 1a114fd | Day 1–4 总结 |
| ea96b21 | 本地 RAG 与来源引用 |
| 2f6b300 | Day 1–5 总结 |
| 896a7d5 | PDF 论文 RAG 与页码引用 |

本次开始时 main 与 origin/main 同步。功能提交后再单独提交本文与验收补充，不嵌入本文自身 hash；最终两个本地新 commit、ahead 2 为预期状态，最终结果在终端复核。没有 push/sync/force push、reset、rebase 或修改旧历史，用户自己手动 push。

## 安全设计

.env、本地 registry、data/local、outputs、knowledge/local 内容均 Git 忽略；public 第三方 PDF 本体也忽略，sources.json 可公开。public PDF 扩展名大小写均覆盖，local papers 只保留可 tracked 的 .gitkeep。

科研文件按 alias 精确授权，PDF 限指定论文目录，文本限项目知识目录；不自动扫描用户电脑。外部科研源只读，图写受限输出。列表/工具结果不向模型暴露原始绝对地址，错误与预览有基础脱敏，不是任意敏感内容识别系统。

Git 忽略不等于 API 不接收：CSV 摘要/派生值和 RAG 命中片段可能发给 DeepSeek。放入私有资料前需确认访问、学习使用与 API 处理授权；公开可访问也不等于可任意重新分发。本文和 Git 不含第三方 PDF 本体，不传播未经核实的 license。

## 当前不足

- TF-IDF 偏字面；未知英文主题误召回、中文检索英文论文漏检真实存在。
- PDF layout parsing 有限，公式、图表、连字、双栏与阅读顺序需复核。
- 无 OCR、无 embedding；不支持所有扫描/加密/复杂 PDF。
- citation identity ≠ claim entailment，模型可能引用对但结论不被支持，甚至把片段不足说成全文不存在。
- all 模式会改变项目历史问题排名；scope 隔离依赖正确模型路由与工具参数，不保证每次自动选择都正确。
- 小开发评估集，没有独立 holdout，没有完整最终答案/引用支持评估。
- 没 Web UI、部署、长期记忆、预算管理或生产级安全审计；网络下载曾 TLS/406/超时，未构建自动恢复系统。
- 当前 CSV 适配是有限格式支持，不是所有模拟格式通吃；当前两曲线未做收敛、误差归因或软件精度比较。

项目定位是经过小范围真实验证的学习原型，不是生产系统。

## 我真正掌握了什么

Codex 已实现：API 接入、工具循环、CSV 分析、alias 隔离、Markdown/PDF loader、分块检索、引用校验、测试、真实 Demo 与文档。这说明项目能运行，不说明我全部独立手写或已经精通。

我应能独立解释/修改：谁执行 Python，call_id 如何对应结果，过零插值为什么需要相邻两点，数据在哪一步发给 API，scope 怎样选输入文档，PDF 为什么按页分块，引用校验能做和不能做什么。

自测：手算一个零点；从 p12 citation 打开实际页面定位一句证据；在临时 fixture 增加空页预测计数；用中英文对照检索解释 coverage；写一个“页码对但主张错”例子；复述为什么未命中不是全文不存在。只有能自己完成这些，才诚实说真正理解。

## 面试 3 分钟介绍

“我是物理本科生，希望把科研数据经验和 LLM 应用开发结合起来。在 Codex 协助下，我做了一个小型 Physics Research Agent CLI，没有先上复杂框架，也没有训练模型。

从普通 DeepSeek API 开始，我加入 Tool Calling：模型只输出工具名与 JSON 参数，本地 Python 执行，通过 call_id 回传，再由模型组织答案。计算器用 AST 白名单，Agent 最多五轮，防止无限循环。

科研部分用 pandas 与 matplotlib，先检查 CSV 结构，再按首次负到正过零定义使用相邻点线性插值。接真实 MuMax3/COMSOL 时发现对比表其实是汇总，追溯原始曲线后重算。通过本地 alias 隔离路径，统一 time/mz/source，但不改原生网格，得到约 73.838 和 72.819 ps。它不证明哪个软件更准确。

检索部分先做最小 Markdown RAG，用字符 2–4 gram TF-IDF，返回程序生成的真实行号；Day 6 接一篇公开 MuMax3 论文，用 PyMuPDF 逐页提取，页内分块，共用原检索器，回答带 p12 等页码引用。当前数据走 Python，项目历史走 Markdown，论文内容走 PDF。

后端拒绝未检索的引用、任意文件路径和文档执行指令。105 项测试通过，真实 API 跑了九类问题与综合问题。评估并不完美：PDF 六正例命中，但一个英文负例误召回；联合库也挤掉一个历史来源。scope 分流保住项目范围回归，但 citation 对不等于每句话被证据支持。

所以我把它作为可解释、可验证的学习原型，而不是自动科研结论生成器。下一步先亲自消化代码、补独立问题集，再做授权公开资料的最小求职 Web 展示。”

## 面试问题

### 基础与 Day 5 回顾

1. API/JSON 是什么？API 是程序交互接口，JSON 是交换结构化参数与结果的格式。
2. Tool Calling 谁执行？LLM 请求，本地 Python 校验并执行；不是模型直接进入电脑。
3. schema 是否保证安全？不保证，后端仍要校验类型、路径、数值与权限。
4. 为什么不用任意 eval？不可信表达式可能执行代码，本项目只解释 AST 白名单。
5. DataFrame 是什么？有列名、类型与索引的二维表，先 inspect 再分析。
6. switching time 是什么？本项目首次负到正过零，用相邻点线性插值，不等于达到 +1。
7. 101 行是否时间点相同？不一定；必须看具体时间列，不预先重采样。
8. alias 的意义？只在私有配置精确授权文件，模型不用知道真实地址。
9. RAG 是什么？检索相关资料，临时放入本轮 context 后生成；不修改权重。
10. chunk/overlap 是什么？片段与有限重复语境，兼顾定位和上下文长度。
11. 为什么用 char n-gram TF-IDF？中文与混合英文无需额外分词，基线透明；但偏字面。
12. embedding 区别？学习语义表示，可改善改写匹配，但不自动解决引用和授权。
13. grounded answer 是什么？主张限制在本轮证据能支持的范围，不能凭常识冒充资料。
14. 引用由谁生成？程序依据读取来源生成，模型只能原样使用本轮返回引用。
15. 检索不到怎么办？明确当前证据不足，不扩大目录权限或伪造结论。
16. Prompt injection 是什么？资料夹带改变行为/权限的指令；资料不是系统指令。
17. RAG 与 Tool Calling 区别？RAG 是检索增强方法，Tool Calling 是交互机制，可用后者调用前者。
18. 当前数据为何不能只查文档？文档可能过时，当前结果必须读取当前授权文件计算。
19. Hit@4 是模型准确率吗？不是；仅题级可接受来源/页进入 Top-4。
20. 阈值是概率吗？不是，cosine 与 coverage 不是正确率校准。
21. Git 忽略是否完全保密？不是，命中片段/摘要可能发 API，必须确认授权。
22. 为什么不立刻上框架？当前瓶颈是检索泛化与证据支持，不是抽象层数量。

### Day 6 新增

1. PDF 如何解析？PyMuPDF 打开文档，逐页 get_text("text")，保存 index+1 与来源。
2. PyMuPDF 是什么？处理 PDF 页面、文字和渲染的 Python 库，本项目也用它创建自产 fixture。
3. 为什么 citation 用 page？PDF 阅读器页序稳定可定位，提取行号未必与排版行对应。
4. 扫描 PDF 怎么办？当前标记 empty_or_scanned，不伪造文字，后续再评估 OCR。
5. chunk 为什么不跨页？防止一个片段多页却只引用一页，破坏真实定位。
6. PDF RAG 与 Markdown 区别？loader/定位元数据不同；后面的 TF-IDF、Top-K、生成与校验共用。
7. 为什么不提交论文 PDF？避免默认重新分发第三方全文与扩大仓库；提交来源和代码即可复现。
8. 版权与访问怎样考虑？公开可访问不等于自由再分发；未核实许可证就明确未知，私有资料需授权。
9. 为什么不马上 OCR？科学公式和单位容易错，先把文本型 PDF 的证据链做清楚。
10. 为什么不马上 embedding？控制变量，先理解提取/页码/分块；未来用独立评估证明收益。
11. 双栏错序怎么办？人工核对页面，评估按 blocks/位置排序的小适配，不擅自改科学含义。
12. 引用页对但答案错怎么办？身份校验不够，逐句核对支持关系，建立 claim entailment/人工审核集。
13. 论文和当前数据冲突怎么办？先分清版本、对象、单位与判据，各保留来源，不自动认定一方错。
14. 五轮与五个工具相同吗？不同，一次模型响应可请求多个工具，执行次数可大于循环轮数。
15. 为什么负例仍被检索？长英文论文中通用 n-gram 重叠大；found=true 仍需判断是否支持问题。
16. 是否能断言全文没有某主题？Top-K 不足以证明全文缺失，只说当前检索片段证据不足。

## Day 7 建议

先面向求职展示：亲自跑三类来源与综合问题，录一个短 CLI Demo；精简 README，明确事实来源、隐私边界与失败指标。简历写成“在 Codex 协助下开发科研 Agent 原型，完成真实数据与论文页码证据链”，不要写生产系统或全部独立研发。

优先补一小组不参与调参的 holdout，评价页命中、拒答、路由与最终主张支持。再做一个只用公开论文和 synthetic 数据的最小 Web Demo，保护 API Key，不挂接私有 registry。演示应显示工具、证据、单位与不足提示，不同时加入 OCR、embedding、多 Agent、数据库和部署大改。

准备面试：读懂 run_agent、curve_analysis、chunk_document、KnowledgeRetriever.search 与 pdf_documents；解释两处真实失败和工程选择，能独立改一个测试比展示功能数量更重要。

## 本地复现入口

依赖：Python 3.12.14、openai 3.22.1、python-dotenv 1.2.4、pandas 3.0.6、matplotlib 3.11.2、scikit-learn 1.9.1、PyMuPDF 1.28.2；模型 deepseek-flash，Responses API。

在项目根目录执行：

```powershell
conda run --no-capture-output -n agent python -m pip install -r requirements.txt
conda run --no-capture-output -n agent python run_agent.py
conda run --no-capture-output -n agent python run_rag.py
conda run --no-capture-output -n agent python run_pdf_rag.py
conda run --no-capture-output -n agent python scripts/inspect_pdf.py mumax3
conda run --no-capture-output -n agent python scripts/evaluate_rag.py
conda run --no-capture-output -n agent python scripts/evaluate_rag.py --include-papers
conda run --no-capture-output -n agent python scripts/evaluate_pdf_rag.py
conda run --no-capture-output -n agent python -m unittest discover -s tests -v
conda run --no-capture-output -n agent python -m compileall src tests scripts run_agent.py run_rag.py run_pdf_rag.py
git status -sb
git log --oneline -10
```

独立检索 CLI 不需密钥；PDF integration 需手动下载公开 PDF。真实 Agent 需密钥/网络，真实数据 Demo 需本地授权 registry；单元测试不需要这些条件。两项带已知失败的评估命令退出 1 是真实记录，不是安装或单元测试失败。
