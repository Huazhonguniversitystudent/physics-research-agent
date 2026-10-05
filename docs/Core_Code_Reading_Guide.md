# 核心代码阅读清单

目标不是背全部代码，而是能画出调用链、解释边界，并在不依赖 Codex 的情况下完成一个小改动和对应测试。

## 1. `run_agent.py`

需要看懂：CLI 如何读问题、何时创建 client、异常如何展示。能说明它只是入口，核心循环不应该复制到 CLI 或 Web。

## 2. `src/agent.py`

需要看懂：system instructions、tool schema、`TOOL_FUNCTIONS` 分发、`function_call` / `function_call_output`、`call_id`、`MAX_STEPS`、citation 集合、`collect_trace` 向后兼容。能手画“模型请求 → Python 执行 → 结果回传 → 模型回答”。

## 3. `src/tools/calculator.py`

需要看懂：为什么用 AST 白名单而不是 `eval`；允许哪些节点、函数和常数；危险表达式在哪里被拒绝。练习：增加一个安全函数并先写测试。

## 4. `src/tools/curve_analysis.py` / `find_zero_crossing`

需要看懂：有限数值检查、时间排序、重复时间、方向判断和相邻点线性插值公式。能手算两个点之间的过零时间，并解释 switching time 不等于达到 +1。

## 5. `src/tools/data_sources.py`

需要看懂：registry 为什么只给模型 alias、绝对路径在哪里解析、编码/分隔符如何识别、输出如何脱敏。能解释“Git ignore 不等于 API 不会看到摘要”。

## 6. `KnowledgeRetriever.search`

需要看懂：char n-gram TF-IDF、cosine similarity、query coverage、threshold、Top-K 和每来源限额。能解释 found=true 为什么不代表证据支持，以及 hard negative 为什么误召回。

## 7. `chunk_document`

需要看懂：Markdown 标题、完整行、目标长度、overlap、真实行号和 PDF 页内分块。能解释为什么 PDF chunk 不跨页。

## 8. `src/rag/pdf_documents.py`

需要看懂：允许目录、`paper_id`、`sources.json`、1-based 页码、文本提取状态和损坏/加密 PDF 的处理。能解释为什么公开可访问不等于可再分发。

## 9. `src/rag/citations.py`

需要看懂：正则提取、allowed set、missing/invalid 的区别。必须能举出“citation identity 通过但 claim 不被支持”的例子。

## 10. `web_app.py` 与 `src/web/public_mode.py`

需要看懂：Public Mode 默认值、tool schema 收窄、后端二次验证、synthetic 固定路径、trace 脱敏、无 API 降级。能说明为什么前端隐藏按钮不足以形成安全边界。

## 建议阅读顺序

1. 先跑一个 calculator 示例，沿调用链下断点或加临时日志。
2. 手算并运行一个过零 fixture。
3. 用 `run_rag.py` 定位一条真实行号引用。
4. 用 `run_pdf_rag.py` 打开返回页核对证据。
5. 修改一个测试 fixture，先预测结果，再运行单测。
6. 阅读 Day 7 holdout 的四个失败，提出改进方案但不要改写历史结果。

## 自测标准

- 不看文档能解释 `call_id` 的作用。
- 能写出过零插值公式并手算。
- 能区分 current data、project docs、papers 三条路径。
- 能解释 Public Mode 的前后端双层限制。
- 能说明 unit test、retrieval Hit@4、citation validity 和 grounding 的区别。
- 能诚实指出至少三个模型/检索失败案例。
