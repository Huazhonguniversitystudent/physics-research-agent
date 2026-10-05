# Physics Research Agent 面试准备

## 30 秒项目介绍

我做了一个面向物理科研的可验证 AI Agent 原型。DeepSeek 负责选择工具，本地 Python 负责数学、科研 CSV 和微磁学曲线计算，Markdown/PDF RAG 负责提供真实行号或页码证据。项目默认使用 Public Mode 保护私人数据，并用 113 项单测和独立 holdout 分项验证；我也保留了改写检索和 hard negative 的失败结果。

## 1 分钟项目介绍

这个项目解决的是科研问答里“当前数据、项目历史和论文证据混在一起”的问题。我用 DeepSeek Responses API 做 Tool Calling：模型只决定工具名和参数，Python 用受限函数执行计算并回传结果；科研侧支持 CSV 结构检查、首次过零线性插值、绘图，以及通过 alias 接入授权的 MuMax3/COMSOL 数据。

检索侧没有直接上复杂框架，而是做了可解释的 char n-gram TF-IDF baseline。Markdown 返回真实行号，PDF 用 PyMuPDF 逐页解析并返回真实页码，后端只接受本轮检索过的 citation。Streamlit Demo 默认只开放 synthetic、公开文档和公开论文；评估把单测、routing、retrieval、负例、citation validity 和人工 grounding 分开，独立 holdout 也如实暴露了 Docs 2/4、Negative 1/4 的不足。

## 3 分钟项目介绍

我做 Physics Research Agent，是因为物理科研问题经常同时涉及三类事实：当前 CSV 的数值、项目文档中的历史记录、论文中的一般方法。如果只让 LLM 生成，它容易把旧值当当前值、把论文方法当作本次实验结论，或者给出无法核查的引用。

架构上，我把职责拆开。DeepSeek Responses API 负责选择工具；`src/agent.py` 解析 `function_call`，本地 Python 真正执行 calculator、电子能量、CSV 检查、过零插值和绘图，再用同一个 `call_id` 通过 `function_call_output` 回传。真实科研数据不把绝对路径交给模型，而是通过本地 registry 和 alias 精确授权；Web 默认 Public Mode，后端同时收窄 schema、校验数据集并排除 private 文档。

RAG 部分先做 Markdown，再扩展到 PDF。两者共用字符级 2–4 gram TF-IDF 和 Top-K；区别在 loader 和定位元数据：Markdown 保留真实行号，PDF 按物理页分块，引用形如 `[paper:mumax3:p12]`。Agent 只允许使用本轮返回过的引用，但我明确把 citation identity 和 claim entailment 分开：引用字符串正确，不代表每句话都受支持。

科研案例中，授权的粗网格曲线重新计算得到 MuMax3 约 73.838 ps、COMSOL 约 72.819 ps；这只是首次负到正过零的时间差，不证明谁更准确。公开 Web 不展示这些真实文件，只用 synthetic 曲线和公开 Mumax3 论文。

验证上有 113 项确定性单测。Day 5 dev set 是 8/8 正例、4/4 负例；Day 6 PDF 固定集 Page Hit@4 6/6，但英文负例只有 1/2；Day 7 独立 holdout 是 Routing 4/4、Docs 2/4、PDF 4/4、Negative 1/4，8 个生成回答人工标为 5 Supported、2 Partially Supported、1 Unsupported。我没有用 holdout 调参，因为失败本身说明 TF-IDF 对改写和 hard negative 不够稳。

项目开发中我大量使用 Codex 协助编码和文档。我不会说全部代码都能从零默写；我的责任是持续参与需求、物理背景和验收，并通过亲自运行、读核心模块、修改 fixture、解释调用链和失败案例，把 AI 生成的实现转化为自己真正理解的能力。

## A. Python / API

### 1. DeepSeek 是怎样接入的？

项目用 OpenAI Python SDK 的兼容接口连接 DeepSeek，服务端从 `.env` 读取 Key，并调用 Responses API。Key 不进入前端、URL、trace 或 Git；没有 Key 时 Web 显示固定提示，不输出敏感值。

### 2. JSON 在 Tool Calling 里承担什么角色？

模型返回工具名和 JSON 参数，Python 用 `json.loads` 解析并验证必须是对象。JSON 只是结构化请求，不代表模型已经执行代码；真正的函数分发发生在本地映射表。

### 3. `call_id` 为什么重要？

一个响应里可以同时出现多个函数请求，`call_id` 把每个 `function_call_output` 精确关联回原请求。若只靠顺序或工具名匹配，多工具并行时容易把结果接错。

### 4. 为什么限制 `MAX_STEPS=5`？

它防止模型反复调用工具形成无限循环，也限制延迟和费用。达到上限时程序返回明确失败，不把“还在思考”伪装成完成。

## B. Agent / Tool Calling

### 5. 谁真正执行 Python？

LLM 只提出工具名和参数，本地 `src/agent.py` 查找函数并执行。执行结果再回传给 LLM，由模型组织自然语言答案；模型没有直接获得本机 shell 权限。

### 6. Tool schema 能保证安全吗？

不能。Schema 能约束模型应当怎样请求，但不可信输入仍需后端验证工具名、类型、路径、范围和数值；Public Mode 也在执行前做二次检查。

### 7. 普通物理问题为什么不总调用工具？

概念解释不需要确定性数值时，额外工具会增加延迟并制造无关结果。Instructions 要求只有明确数值任务或不计算无法完成时才调用工具。

### 8. Web Tool Trace 是怎样实现的？

`run_agent(..., collect_trace=True)` 在保持旧字符串返回兼容的同时返回答案和经过脱敏的 trace。trace 只保留简化参数、结果摘要和 citation，不抓 stdout，也不显示完整 chunk、密钥或绝对路径。

## C. RAG

### 9. 为什么先用字符级 TF-IDF？

它无需外部 embedding 服务，中文和中英混合文本不用额外分词，而且权重和失败原因容易解释。代价是偏字面，对同义改写、跨语言和 hard negative 不够稳，Day 7 holdout 已真实暴露这一点。

### 10. Markdown 和 PDF RAG 有什么共同点与区别？

它们共用 chunk、TF-IDF、cosine 排序和 Agent citation 校验。区别在 loader 与定位：Markdown 用真实文件行号，PDF 用 PyMuPDF 逐页提取并引用物理页码，且 chunk 不跨页。

### 11. 为什么 PDF chunk 不跨页？

如果片段跨两页却只标一个页码，读者无法判断哪一页支持结论。按页重置分块牺牲少量跨页上下文，换来可核查的定位边界。

### 12. Citation 校验能证明什么、不能证明什么？

它能证明引用字符串属于本轮检索返回的允许集合，并拒绝 fake page 或缺失引用。它不能证明该片段语义上支撑每句话，也不能判断模型是否做了过强因果推断。

## D. Scientific Computing

### 13. Switching time 在项目中怎样定义？

定义为选定 `mz` 首次从负值达到或穿过零的时间。程序找相邻两点并做线性插值；它不等于磁化达到 +1，也不是所有研究都必须采用的唯一判据。

### 14. 线性插值公式是什么？

对 `(t1,m1)` 与 `(t2,m2)`，零点为 `t1 + (0-m1)(t2-t1)/(m2-m1)`。使用前要检查有限数值、时间重复和 crossing 方向，否则公式可能没有物理意义或发生除零。

### 15. 为什么相同行数不代表采样网格相同？

两个 CSV 都有 101 行，只说明点数相同，不说明每一行的时间值相同。对比前要检查实际时间列；不能按行号直接把不同时间点配对。

### 16. 真实 MuMax3/COMSOL 结果说明了什么？

粗网格当前曲线的首次过零约为 73.838 ps 与 72.819 ps，差约 1.019 ps。这个结果只描述两份数据，不证明某软件更准确，也不足以给差异归因。

## E. 安全

### 17. Public Mode 怎样防止访问私人 registry？

默认环境值为 true，模型只看到公开工具 schema；后端还拒绝 private 工具，并把允许数据集规范化到固定 synthetic 路径。公开文档/PDF loader 同时设置 `include_local=False`，所以安全边界不只靠页面隐藏。

### 18. Alias registry 解决了什么问题？

用户在本地把授权数据映射为 alias，模型只传业务名，不传 Windows 绝对路径。Python 精确解析登记项、拒绝未注册名称和路径偏移，并在结果中隐藏常见绝对路径。

### 19. 为什么 Git ignore 不等于隐私保护？

Git ignore 只防止文件被版本控制，不阻止程序读取或把命中摘要发送给 API。私有资料放入 local 目录前，仍需确认授权、API 处理边界和输出内容。

### 20. Prompt injection 防护做到什么程度？

文档被标为 UNTRUSTED DATA，内容会转义并且 loader 不执行 `eval`、subprocess 或文本指令。它只是基础隔离，不是生产级防注入；多租户场景仍需要权限系统、内容策略和审计。

## F. Evaluation

### 21. 为什么 113 项单测不等于模型可靠？

单测主要验证确定性函数、路径边界和 mock Agent 交互，不覆盖所有真实语言输入。模型路由、生成与 grounding 需要单独的固定问题和人工审阅。

### 22. 为什么不报告一个总准确率？

Routing、source Hit@4、page Hit@4、negative rejection、citation validity 和 grounding 的分母与含义不同。把它们平均会隐藏系统到底在哪一层失败。

### 23. Holdout 为什么先哈希再运行？

SHA-256 证明正式运行所用题集的具体内容，防止看到结果后悄悄删题或改预期。哈希不能消除所有选择偏差，但提供了基本的可追溯性。

### 24. 人工 grounding 有什么局限？

本次只有 8 个回答、单人标注，也没有盲评或一致性统计。它适合发现明显扩写和拒绝答案，不应称为稳定的模型质量基准。

## G. 项目失败案例

### 25. 这个项目有哪个地方做得不好？

检索 baseline 对改写和 hard negative 较弱，Day 7 Docs 只有 2/4，Negative 只有 1/4；生成侧 citation identity 也不能验证语义。Web 是单机原型，没有认证、长期记忆、OCR、部署监控或生产级访问控制。

### 26. 模型实际犯过什么错？

它曾把 `sorted=false` 误读成“未排序”，自行添加工具未返回的百分比，并从采样差异推断时间差成因。它也曾把“当前 Top-K 证据不足”说成“论文全文没有”，说明提示和引用身份检查都不能完全约束表述。

### 27. 为什么 PDF RAG 负例只有 50%？

Day 6 两个负例中，中文 GPT-6/量子霍尔被拒绝，但英文 Mozart 题在长英文论文里与通用 n-gram 高度重叠，产生误召回。我们没有为该题单独抬阈值或硬编码关键词，因此诚实保留 1/2。

### 28. 为什么 all scope 是 7/8？

加入 104 个 PDF chunks 后，联合索引的候选空间发生变化，一个 Day 4 历史值来源被论文和 README 片段挤出 Top-4。项目通过显式 `project_docs` / `papers` scope 缓解实际路由，但不能声称 all scope 没有退化。

## H. 为什么不用 LangChain

### 29. 为什么不用 LangChain？

本项目核心是学习 Tool Calling、分发、检索和引用边界，直接实现更容易看到每一步。引入框架会增加抽象和依赖，却不会自动解决数据授权、grounding 或评估纪律。

### 30. 不用框架会不会重复造轮子？

会有少量基础代码，但当前范围很小，直接实现的维护成本可控。若未来出现多模型、多存储、多工作流和可观测性需求，再评估框架更合理。

### 31. 什么时候会考虑 LangGraph？

当流程真的需要显式状态机、分支恢复、人工审批或长任务 checkpoint 时。现在只有最多五步的工具循环，引入图编排会超过需求。

### 32. 面试官说“手写不工程化”怎么办？

我会说明这是有意选择的透明 baseline，并展示单测、接口边界和失败记录。工程化不是依赖数量，而是需求匹配、可测试、可维护和可解释。

## I. 为什么不用 embedding

### 33. 如果面试官说 TF-IDF 太简单怎么办？

我同意它简单，这正是 baseline 的价值：成本低、可解释、能明确量化失败。下一步应在同一 dev/holdout 纪律下比较 multilingual embedding、hybrid retrieval 和 reranker，而不是口头假设一定更好。

### 34. Embedding 会自动解决负例吗？

不会。语义向量可能改善同义改写，也可能把主题相近但不支持的片段召回；仍需阈值、rerank、拒答、citation 和 grounding 评估。

### 35. 跨语言问题怎样改进？

可比较“查询翻译 + 当前 TF-IDF”、多语言 embedding 与 hybrid BM25/vector。评估必须保留中英文正负例，并记录翻译是否改变原意。

### 36. 换 embedding 时最先保持什么不变？

保持语料、chunk、Top-K 定义和评估题不变，先只替换检索表示，才能做受控比较。若同时改分块、阈值和提示，就无法知道提升来自哪里。

## J. 未来扩展与个人贡献

### 37. 下一步最值得做什么？

第一优先不是加更多 Agent，而是读懂核心代码并建立更好的 evaluation。之后可做 multilingual embedding/hybrid 对照、claim-level grounding 审阅，再考虑 FastAPI 和部署。

### 38. 如何把它变成可部署服务？

可把 Agent 核心放到 FastAPI，前端只传问题；服务端增加认证、配额、日志脱敏、超时、并发与持久化。private mode 不能直接暴露到公网，需要独立权限与数据隔离设计。

### 39. 你个人真正写了多少？

项目的大量实现和文档由 Codex 协助生成，我不应声称全部代码独立手写。我的实际贡献是持续给出需求、物理场景、数据背景和验收反馈；接下来要通过亲自阅读、修改 fixture 和现场解释把实现真正掌握。

### 40. Codex 帮你做了什么？

Codex 帮助了代码结构、测试、调试、文档和自动化验收，也加速了对失败的定位。它不能替我决定科研数据是否可公开，也不能替我承担结果真实性；我需要核对代码、证据、数值和边界，并诚实说明协作方式。

## 如果面试官问：这个项目是不是 AI 帮你写的？

推荐回答：

“是的，开发过程中我大量使用 Codex 作为编码助手，我不会把它包装成全部独立手写。需求拆解、真实物理数据背景和验收由我持续参与；Codex 主要帮助实现、测试和文档。为了确保不是只会展示，我会亲自运行、读核心模块、修改 fixture、手算过零时间，并解释 Tool Calling、RAG 引用和 holdout 失败。如果某段代码我还不能脱离辅助重写，我会明确说还在学习，而不是假装精通。”

回答后应主动准备展示：

1. 画出 `function_call → Python → function_call_output` 调用链。
2. 手算一个两点过零插值。
3. 打开一个真实 citation 并定位原文。
4. 解释为什么 Day 7 Negative 只有 1/4，且为什么没有调参。
5. 现场给一个 fixture 加边界条件并运行测试。
