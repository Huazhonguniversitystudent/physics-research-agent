# Physics Research Agent：Day 1–Day 7 一周学习总结

日期：2026-10-05。项目位于本地 `physics-research-agent` 仓库。这是一份自包含总结，区分已验证能力、失败、限制与仍需本人继续学习的部分。

## 1. 为什么做这个项目

物理科研问答不只有“让模型回答”这一件事。当前数据需要重新计算，项目历史需要查文档，论文方法需要引用证据；三者混用会让模型把旧记录当当前值、把一般论文结论当本次仿真结论，或生成不可核查的数字。

本项目的核心思想是职责分离：LLM 负责决策和语言，Python 负责确定性执行，RAG 负责可追溯证据。目标不是训练大模型或建设生产平台，而是在一周内做出能运行、能解释、能测试、能诚实展示边界的学习原型。

## 2. Day 1：LLM API

第一天建立 Python、JSON、环境变量与 API 的基本链路。项目从 `.env` 读取 `DEEPSEEK_API_KEY`，使用 OpenAI Python SDK 的兼容接口调用 DeepSeek Responses API，并提供最小 CLI 问答。

我理解了 API 请求不是“本地运行模型”：本地程序发送结构化输入，远端模型返回响应；Key 属于服务端凭证，不能写入源码、前端、URL 或 Git。错误处理必须区分缺 Key、网络失败和模型无有效输出。

## 3. Day 2：Tool Calling

第二天增加 `calculator`、`electron_energy_from_voltage` 与最多五步的 Agent Loop。模型返回 `function_call` 的工具名和 JSON 参数，本地 `src/agent.py` 根据映射表真正调用 Python 函数，再用相同 `call_id` 构造 `function_call_output` 回传。

计算器没有使用任意 `eval`，而是解析 AST，只允许白名单运算符、函数和常数。Tool schema 只是请求格式，不是安全边界；后端仍要验证工具名、参数类型和内容。

## 4. Day 3：科研 CSV

第三天用 pandas 读取公开合成 `synthetic_micromagnetics.csv`，先检查列、类型、行数、缺失值和预览，再计算平均磁化曲线首次从负到正穿过零的时间。对相邻点 `(t1,m1)`、`(t2,m2)` 使用：

`t_zero = t1 + (0 - m1) * (t2 - t1) / (m2 - m1)`。

程序检查 NaN、非数值、重复时间、列缺失、少于两点和无 crossing，并标记是否发生排序。matplotlib 只把图写入受限 `outputs/plots`；过零不等于磁化达到 +1。合成列名只是演示标签，不表示真正运行过 MuMax3 或 COMSOL。

## 5. Day 4：真实 MuMax3 / COMSOL

第四天适配用户授权的真实曲线。由于真实 CSV 可能有 BOM、GBK、不同分隔符、列名和采样网格，流程不能套用合成格式，而要先 inspect，再选择列、单位和曲线来源。

本地 `config/data_sources.local.json` 用 alias 精确登记文件，模型只看到 alias，不看到绝对路径。Python 拒绝未登记名字、路径偏移和不安全文件，并把单文件或组合曲线标准化为可分析结构，但不修改原始科研文件。

粗网格 `J=2.5e12 A/m²` 的当前原始曲线重新计算结果：MuMax3 `73.83834774284676 ps`，COMSOL `72.81911124409665 ps`，绝对差 `1.019236498750118 ps`；100 ps 的 `mz` 分别为 `0.9564934` 与 `0.962276697685`。这些结果不证明哪个软件更准确，也不足以给差异归因。

## 6. Day 5：Markdown RAG

第五天实现最小 RAG：允许的 Markdown/TXT → 按标题和完整行分块 → 字符级 2–4 gram TF-IDF → cosine similarity → Top-K。chunk 保留真实 source、标题和 1-based 行范围，引用形如 `[docs/Day2_Tool_Calling.md:L44-L70]`。

检索资料被包在 UNTRUSTED DATA 标签中，内容会转义，不获得执行权限。Agent 记录本轮实际返回的 citation 集合；缺引用或伪造引用会被拒绝。该校验只证明引用身份，不证明每句话的 claim entailment。

Day 5 开发集共 12 题，正例 source Hit@4 8/8、负例拒绝 4/4。题集参与过阈值和规则开发，所以不能称为独立泛化准确率。

## 7. Day 6：PDF RAG

第六天接入公开论文 *The design and verification of Mumax3*（arXiv:1406.7635v3）。PyMuPDF 对 32 个物理页逐页提取文字，页内分块但不跨页，引用形如 `[paper:mumax3:p12]`；Markdown 与 PDF 共用同一个 TF-IDF retriever。

论文目录用 `sources.json` 记录 title、authors、year、source URL 与访问说明。工具只接收 `paper_id`，拒绝任意绝对路径、`..`、UNC 和符号链接偏移。PDF 本体公开可访问但许可未确认，因此不随仓库再分发。

Day 6 PDF 固定集：6 个正例 Page Hit@4 6/6，2 个负例只拒绝 1/2。英文 Mozart hard negative 在长英文论文中被通用 n-gram 误召回；中文直接检索英文论文也会因 coverage 低而漏检。加入 PDF 后 all scope 的 Day 5 来源命中从 8/8 退化为 7/8，说明候选库扩大可能改变排名。

## 8. Day 7：Web Demo 与求职包装

第七天没有继续堆底层 Agent，而是增加 Streamlit 本地 Web：Agent 对话、科研数据 Demo、论文问答三个模式。页面展示答案、简化 Tool Trace 与 citation；没有 API 时明确提示，合成数据和 retrieval-only 尽量仍可展示。

Public Demo Mode 默认开启，只允许普通回答、计算器、合成 CSV、公开项目文档和公开 Mumax3 PDF。后端不只隐藏按钮，还收窄 tool schema、验证工具名与参数、固定 synthetic 路径，并对文本/PDF 设置 `include_local=False`。三张截图均通过真实 Edge/Playwright 浏览器生成，只展示公开内容。

同日建立 16 题独立 holdout、重构求职型 README，并生成视频脚本、GitHub 设置建议、中英文简历描述、面试题库、核心代码阅读清单和投递关键词。

Day 7 功能提交：`e6d5fcf feat: 增加公开安全 Web Demo 与独立评估`。

## 9. 当前完整架构

```text
用户（CLI / Streamlit）
        ↓
DeepSeek Responses API / Agent Loop（MAX_STEPS=5）
        ├─ 普通概念 → LLM 直接回答
        ├─ 确定性任务 → Calculator / Physics / CSV / Micromagnetics tools
        ├─ 项目历史 → Markdown loader → chunk → TF-IDF → 行号 citation
        └─ 论文内容 → PDF loader → page chunk → 同一 TF-IDF → 页码 citation
                                ↓
                      citation identity validator
                                ↓
                         答案 + safe trace
```

当前数据必须由 Python tools 重新读取和计算；项目历史只在文档证据范围内回答；论文问题用 papers scope。scope 分离不是三套算法，而是为同一 retriever 选择不同输入语料。

## 10. 当前真实能力

- DeepSeek API 与 Responses Tool Calling
- 14 个注册工具，Public Mode 暴露其中 9 个公开安全工具
- AST 数学、电子能量、科研 CSV 结构检查、过零插值和绘图
- 授权本地 alias、格式适配、组合曲线、采样和摘要
- Markdown 行号与 PDF 页码 RAG
- citation identity 校验与证据不足拒答
- Streamlit Web 与轻量 trace
- 113 项确定性单测、开发集、PDF 固定集和独立 holdout

它不是大模型训练、生产科研平台、自动论文审稿器或科学真理验证系统。

## 11. 真实科研结果

真实数据只在授权本地使用，不提交仓库，也不出现在公开截图。粗网格案例的过零时间与 100 ps 值见第 5 节；结论必须带来源、方法、数值、单位和插值状态。

公开 Web 使用的 synthetic 曲线实际插值约为 MuMax3 标签 `73.798725 ps`、COMSOL 标签 `72.599363 ps`，绝对差约 `1.199362 ps`。这些标签和数字只验证工作流，不代表真实软件结果。

## 12. RAG Evaluation

| 评估阶段 | 指标 | 结果 | 边界 |
| --- | --- | ---: | --- |
| Day 5 dev | project source Hit@4 | 8/8 | 参与开发调参 |
| Day 5 dev | negative rejection | 4/4 | 参与开发调参 |
| Day 6 PDF fixed | page Hit@4 | 6/6 | 开发集，不是答案准确率 |
| Day 6 PDF fixed | negative rejection | 1/2 | 英文未知主题误召回 |
| Day 6 all scope | project source Hit@4 | 7/8 | 联合库排名退化 |
| Day 7 holdout | routing | 4/4 | 四类路由样例 |
| Day 7 holdout | project source Hit@4 | 2/4 | 改写检索失败 |
| Day 7 holdout | PDF page Hit@4 | 4/4 | 新页面 p10/p11/p17/p19 |
| Day 7 holdout | negative rejection | 1/4 | hard negative 明显不足 |
| Day 7 generated | citation valid | 7/8 | 身份，不是语义支持 |
| Day 7 manual | grounding | 5 S / 2 P / 1 U | 单人、8 题小样本 |

Holdout SHA-256：`1b235726c32510aa2501760c141e293e7ba9a371c5a9867322837c7a42d6ea3a`。正式运行一次后没有调阈值、删题或改 expected page。README/求职文档在正式 run 后完成，因此结果是当时语料快照，后续文档变化不宣称已被该次 holdout 覆盖。

## 13. unittest

Day 6 为 105 项；Day 7 增加 8 项 Web/Public Mode 纯逻辑测试，总计 **113/113 通过**。新增覆盖默认 Public Mode、private tools 拒绝、API Key 不进 trace、路径脱敏、synthetic 固定路径、public-only 文档/PDF 和 `collect_trace` 兼容。

测试运行时 Windows 沙箱的系统临时目录不可写，首次出现 `PermissionError`；将 `TEMP/TMP` 明确指向仓库忽略的 `outputs/test-tmp` 后，未修改测试逻辑即全部通过。`compileall` 与 `git diff --check` 通过。

## 14. 项目失败案例

1. `sorted=false` 曾被模型误读为“未排序”，实际含义是无需重新排序。
2. 模型曾自行添加工具未返回的百分比，后来收紧 instructions，但仍需人工复核派生数值。
3. 模型曾混淆 synthetic 仓库工具与 external alias 工具，说明 schema 描述和后端分发都要清晰。
4. Day 6 PDF 英文负例误召回，negative rejection 只有 50%。
5. PDF 加入后 all scope 来源命中从 8/8 退化到 7/8。
6. 模型曾把“当前 Top-K 证据不足”说成“论文全文没有”，这是过强结论。
7. Day 7 holdout 的 project docs 只有 2/4，暴露同义改写不足。
8. Day 7 hard negative 只有 1/4，暴露字面相似不等于主题支持。
9. Web 首次浏览器验收发现把标量传给 `st.json` 会产生 React 控制台错误；最小改为标量 `st.code` 后复测 0 error。

失败不是附录，而是系统边界和后续学习的主要证据。

## 15. 安全设计

- `.env` 服务端读取且 Git 忽略；不进入 URL、session 可见文本或 trace。
- Public Mode 默认 true，private 工具不出 schema，后端仍二次拒绝。
- 合成数据固定到 `data/examples`，公开检索排除 `knowledge/local` 与本地论文。
- Registry 用 alias 隔离路径；Path.resolve 防穿越、UNC 与链接偏移。
- 文档与 PDF 是 UNTRUSTED DATA，不执行其中指令。
- trace 截断大型结果、隐藏敏感参数与绝对路径。
- `.env`、registry、真实 CSV/PNG、private PDF 与第三方公开 PDF 本体均不提交。

这些是单机原型边界，不是完整身份认证、租户隔离、审计或生产级防注入。

## 16. 我真正理解了什么

我应该能解释：API 与本地程序的边界；`call_id` 如何对应结果；为什么不能 `eval`；过零插值的公式和边界；相同行数为什么不等于相同时间网格；alias 解决什么；TF-IDF/Top-K 的含义；PDF 为什么按页分块；citation identity 与 claim entailment 的区别；为什么 holdout 失败后不能调参。

理解的证据不是“仓库里有代码”，而是能亲自运行、手算、定位引用、改一个 fixture、预测测试变化并解释失败。

## 17. 哪些还是 Codex 帮我实现、我需要继续补

这一周大量代码、测试、调试、文档和浏览器自动化由 Codex 协助完成。我不能据此声称独立掌握 OpenAI SDK、Streamlit、路径安全、RAG 评估或所有 Python 工程细节。

我需要亲自读 `run_agent.py`、`src/agent.py`、calculator、curve analysis、data sources、retriever、chunk、PDF loader、citation validator 和 Web Public Mode；独立完成至少一个新 fixture、一个小功能与测试，再进行模拟面试。

## 18. 项目当前不足

- char TF-IDF 不理解完整语义，跨语言与改写不足
- hard negative 拒绝弱，threshold 不能一刀切
- 只有一篇公开论文，无 OCR，双栏/公式/图表解析有限
- citation identity 不验证 claim entailment
- 人工 grounding 样本少、单人标注
- 没有长期记忆、embedding、reranker、数据库
- 没有 FastAPI、云部署、认证、配额、监控和生产安全
- 模型回答具有随机性和扩写风险
- Holdout 正式 run 后仍有 README/作品文档变化，结果只代表当时快照

## 19. 面试 3 分钟介绍

“我做了一个 Physics Research Agent，解决科研问答里当前数据、项目历史和论文证据容易混用的问题。DeepSeek 只负责选工具，本地 Python 真正执行计算；真实数据通过 alias 授权，不把绝对路径给模型。科研侧用 pandas 做结构检查和首次过零线性插值，粗网格真实曲线约为 73.838 与 72.819 ps，但我明确不把差异解释成软件精度。

检索侧从透明 baseline 开始：Markdown 与 PDF 共用 char n-gram TF-IDF，前者返回真实行号，后者用 PyMuPDF 按页提取并返回页码。后端只接受本轮检索过的 citation，但我把引用身份与语义支持分开。Streamlit 默认 Public Mode，只开放 synthetic、公开文档和公开论文。

验证有 113 项单测和分层评估。Day 7 独立 holdout 中 Routing 4/4、PDF 4/4，但 Docs 2/4、Negative 1/4；我没有为了分数调参，而是把失败写进 README。开发大量使用 Codex，我不会声称全部独立手写；我通过亲自运行、读核心代码、修改 fixture 和解释失败来建立真正能力。”

## 20. 简历项目描述

- 基于 DeepSeek Responses API 实现 Tool Calling 与五步 Agent Loop，由 Python 受限工具完成数学、物理量及科研 CSV 的可靠计算。
- 适配授权 MuMax3/COMSOL 曲线并以 alias 隔离本机路径；实现首次过零线性插值、单位处理、绘图及 public/private 数据边界。
- 构建字符级 TF-IDF Markdown/PDF RAG 与引用校验，完成 113 项单测及独立 holdout；如实记录 hard negative 与改写检索失败。

## 21. 下一周建议

未来 2–4 周不要继续按“Day 8”堆功能，按能力闭环推进：

### 第 1 周：代码内化与 Python 基础

- 按核心阅读清单走通十个模块。
- 复习函数、类、异常、类型、文件、JSON、pandas、unittest。
- 独立增加一个安全 calculator 函数和测试。
- 手写过零插值与三个边界 fixture。

### 第 2 周：API / HTTP 与工程

- 学习 HTTP 方法、状态码、超时、重试、鉴权和限流。
- 用一个最小 FastAPI 包装公开 calculator，不接 private 数据。
- 增加结构化日志、超时和错误分类，练习 curl 与 API 测试。

### 第 3 周：RAG 深入与受控实验

- 建立新的 dev paraphrase/hard-negative 集，不改 Day 7 历史 holdout。
- 比较 query translation、multilingual embedding、hybrid retrieval、reranker。
- 一次只改一个变量，报告 Hit@K、negative rejection、延迟和成本。

### 第 4 周：Evaluation、部署与投递

- 扩展多篇公开论文和双人 grounding 标注。
- 学习 claim-level evaluation、日志脱敏与部署安全。
- 部署仅使用公开数据的版本，保留 private mode 本地化。
- 每周投递 20–30 个匹配岗位，做两次模拟面试，并根据真实追问补基础。

最终目标不是“仓库功能最多”，而是能够独立解释、修改、验证并诚实陈述一个可工作的系统。
