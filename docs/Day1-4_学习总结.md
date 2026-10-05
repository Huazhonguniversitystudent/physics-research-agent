# Physics Research Agent：Day 1–Day 4 学习总结

记录日期：2026-10-05。本文自包含：读者不需要先读仓库其他文档。所有“实际结果”指当前本地项目验证，不把合成数据当成真实模拟，不把自动生成的代码当成学习者已独立掌握的能力。

## 一、项目目标

这是一个物理本科生用于学习 AI Agent，并准备 AI Agent / LLM 应用开发实习的小型项目。目标不是训练大模型，而是把已有模型与可靠的 Python 工具连接起来，完成“问题 → 数据检查 → 数值计算 → 科研解释”的闭环。

四天的主线是从普通 LLM API，发展到 Tool Calling、科研 CSV 分析，最后接入本机已有的真实微磁学结果。坚持小而可跑，不引入 LangChain、LangGraph、多 Agent 或生产级平台；今天没有 RAG、论文阅读和 Web UI。

## 二、Day 1：LLM API

Day 1 包括 Python 环境、变量与函数、JSON、API Key、请求和响应的基础练习。主要文件为 `main.py`、`first_llm.py`、`requirements.txt`；私有 Key 放在 `.env` 中，由 python-dotenv 加载，不写进源码。

```text
用户 → Python → API 请求 → DeepSeek → Response → Python 显示回答
```

JSON 是传递结构化信息的格式，不是 Python 本身。API 返回的 response 是 SDK 对象，需要按接口读取文本或工具调用，不能把整段响应都当成最终答案。

这一阶段能问答，但模型不能可靠访问本机 CSV，也不能因为说“算好了”就证明执行过数学计算。

## 三、Day 2：Tool Calling

Tool Calling 的分工是：LLM 决定“要哪个工具、参数是什么”，Python 真正执行函数，把结果交给 LLM，最后 LLM 组织语言。模型输出 `{"expression": "12345 * 6789"}` 并不等于它自己执行了计算。

`calculator` 使用 Python AST 白名单处理受支持的运算、数学函数和常数，不执行任意 `eval()`。实际乘法工具返回 **83810205**。

`electron_energy_from_voltage` 计算电子通过给定电势差获得的能量，输出 eV 和 J。它是明确公式的教学工具，不是通用物理求解器。

`src/agent.py` 定义 schema、分发映射和 Agent Loop；`run_agent.py` 是 CLI 入口。循环使用 DeepSeek Responses API 的 `function_call` 和 `function_call_output`，保留调用及其 call_id，让模型知道哪个结果对应哪个请求。

`MAX_STEPS=5` 限制最多五轮模型请求，防止无穷循环和失控调用。普通概念问题直接回答；工具错误会回传清晰信息，模型可修正参数，但修正并非必然成功。

## 四、Day 3：科研 CSV

pandas 将 CSV 读成 DataFrame，可按列检查类型、行数和缺失值；matplotlib 将选定列画成图。工具先 inspect，再算数，避免直接猜列名。

`data/examples/synthetic_micromagnetics.csv` 是合成示例：用 `tanh((t-t_switch)/5)` 生成两列，时间 0–100 ps、间隔 1 ps、101 行。`mumax3_mz` 和 `comsol_mz` 只是演示列名，**不表示真的运行了 MuMax3 或 COMSOL**。

本项目将 switching time 定义为磁化平均值 mz 首次负到正过零的时间。相邻点满足 `m1<0`、`m2>=0` 时，用

```text
t_switch = t1 + (0 - m1) × (t2 - t1) / (m2 - m1)
```

其中 t1/t2 是区间时间，m1/m2 是其磁化值。它是局部线性估计，不是测量到的无限精度零点；起始值为零但没有之前负值，不视为已经确认负到正过零。

| Synthetic 曲线 | 实际线性插值结果 |
| --- | --- |
| mumax3_mz | 73.79872503161886 ps |
| comsol_mz | 72.59936292317492 ps |
| 差值 | 1.1993621084439354 ps |

生成设定值是 73.8/72.6 ps；离散采样后插值会略有差异。不能拿这张合成图评判真实软件精度。

路径安全方面，Day 3 限定 `data/examples/` 和 `data/local/` 的 CSV；拒绝任意绝对路径、路径穿越和解析后逃离目录的文件。PNG 只能写 `outputs/plots/`，文件名不允许路径。NaN、非数值、重复时间和没有 crossing 会明确报错，未排序时间会重排并标记。

## 五、Day 4：真实科研数据

本地 registry 位于被 Git 忽略的 `config/data_sources.local.json`。公开模板是 `config/data_sources.example.json`，只用占位路径；模型只收到 alias，不收到注册绝对路径。读取权限来自用户明确登记的文件，不来自模型任意输入。

实际只读发现两份汇总表 `FEM_FDM_J2.5E12对比.csv`、`FEM_FDM_Jc对比.csv`，各 3 行。它们不是时间曲线，所以进一步追溯并接入两份原始曲线：

- `mumax3_j25_coarse`：`MuMax3_粗网格_J2.5E12_体积平均.csv`。
- `comsol_j25_coarse`：`COMSOL_粗网格_J2.5E12_体积平均.csv`。
- `fem_fdm_j25`：上述两个成员的组合。
- `fem_fdm_j25_summary`、`fem_fdm_jc_summary`：原汇总表检查入口。

Adapter 位于 `micromagnetics.py`：先精确匹配再规范化识别列，将两份数据映射成 `time/mz/source`。真实文件识别到 `time_ps/avg_mz`，单位 ps，每份 101 行，组合 202 行。

两者采样点数量相同，但 MuMax3 存在非整数时间，COMSOL 为整数时间。标准化不会先强制对齐，不改变原生采样；比较时分别寻找自己的过零区间。

支持 UTF-8、BOM、GBK/CP936，逗号/制表符/分号。MuMax3 本次是 UTF-8 BOM，COMSOL 是 UTF-8，都是逗号。列名不确定时要求指定；单位不确定标 `unknown`，不能默认 ps。

| 真实粗网格 J=2.5e12 A/m² | MuMax3 | COMSOL |
| --- | --- | --- |
| 首次负到正过零 | 73.83834774284676 ps | 72.81911124409665 ps |
| 100 ps 的 mz | 0.9564934 | 0.962276697685 |

COMSOL 过零更早，差 **1.019236498750118 ps**。过零时间使用线性插值；100 ps 两者都恰好有原始采样点，所以即使取值方法设置为 linear，`interpolated=false`，直接返回采样值。

以上与历史约 73.84/72.82 ps、0.95649/0.96228 一致；与当前汇总表粗网格行的四个值逐项比较，读入浮点表示下误差均为 0.0。没有修改算法迎合参考值，也没有重跑模拟。

真实图 `outputs/plots/fem_fdm_j25_mz_comparison.png` 已实际生成并查看，含坐标、图例、标题、网格。真实 CSV 和 PNG 都不提交；四份真实 CSV 分析前后的 SHA-256 一致，确认原文件未改。

新增 `summarize_magnetization_curve` 返回初末值、极值、负到正 crossing 数与首个时间；`sample_value_at_time` 支持 nearest/linear，禁止外推。算法复现只说明当前文件/判据一致，不证明两个软件谁更正确，不包含误差收敛或物理机制研究。

## 六、项目当前架构

```text
physics-research-agent/
├── main.py、first_llm.py          # Day 1 记录
├── run_agent.py                  # Day 4 CLI
├── requirements.txt、README.md
├── .env                         # 私密，忽略
├── .gitignore
├── config/
│   ├── data_sources.example.json # 可公开模板
│   └── data_sources.local.json   # 本机授权，忽略
├── src/
│   ├── agent.py                  # instructions/schema/循环/分发
│   └── tools/
│       ├── calculator.py         # AST 白名单计算
│       ├── physics.py            # 电子能量
│       ├── scientific_data.py    # 仓库 CSV 与统一绘图
│       ├── curve_analysis.py     # 共享 crossing、排序、数值校验
│       ├── data_sources.py       # registry、读取、inspect、路径隐藏
│       └── micromagnetics.py     # 识别/标准化/比较/取值/摘要
├── data/
│   ├── examples/                 # 合成示例，不含真实数据
│   └── local/                    # 私有缓存，忽略内容
├── scripts/generate_synthetic_data.py
├── outputs/plots/                # 生成 PNG，忽略
├── tests/
│   ├── test_agent.py、test_calculator.py、test_physics.py
│   ├── test_scientific_data.py
│   ├── test_data_sources.py、test_micromagnetics.py
│   └── fixtures/                 # 小型 synthetic CSV
└── docs/
    ├── Day3_Scientific_Data_Tools.md、Day3_Verification.md
    ├── Day4_Real_Scientific_Data.md
    ├── Day4_Real_Data_Validation.md
    └── Day1-4_学习总结.md          # 本文
```

外部真实原文件在项目之外，只读，不出现在上述公开数据目录。内部标准化表只是进程内 DataFrame，没有复制成可提交真实 CSV。

## 七、Agent 工作流程

```text
用户问题
  ↓
LLM 判断是否需要工具
  ├─ 不需要：直接回答，例如蓝天的瑞利散射
  └─ 需要：Tool Selection（工具名 + JSON 参数）
       ↓
     Python 分发与校验 → 授权科研数据 → 计算结果/明确错误
       ↓
     function_call_output 回传给 LLM
       ↓
     下一次工具调用，或 Final Answer
```

程序不按问题关键词伪造工具选择。schema 是描述参数的 JSON 结构，函数映射是实际可调用的 Python 函数，两者要对应；schema 不能替代后端真实校验。

在工具回传之前隐藏常见绝对路径，但只传摘要也仍是 API 数据传输。当前每个用户问题建立新的 conversation，并不是跨问题长期记忆。

## 八、我现在真正会了什么

从初学者角度，可以据此练习复述：API 是程序请求服务的入口；JSON 描述参数；模型只提出工具请求；Python 执行；pandas 检查列；插值从相邻点估计零点；Git 保存代码版本。

但“项目里已经有功能”与“我能独立写出功能”是两件事。此项目的开发、适配和测试由 Codex 协助完成，不能因此自称已熟练掌握 SDK、路径安全、单元测试和真实 CSV 适配；需要自己跑一次、读懂关键函数、修改一个 fixture 并解释结果。

建议自测：不看参考解释一次 call_id 为什么必要；用两个点手算 crossing；说明为什么同样 101 行不意味着同样时间点；故意传未注册 alias 并读懂报错。做得出来，才是可在面试中说“我理解了”的证据。

## 九、项目当前技术栈

运行环境为 Conda `agent`、Python 3.12.14。项目使用 DeepSeek Responses API，当前配置模型 `deepseek-flash`，通过 OpenAI Python SDK 调用兼容接口；没有调用 OpenAI 模型来替代 DeepSeek。

当前 `requirements.txt` 固定 openai 3.22.1、python-dotenv 1.2.4、pandas 3.0.6、matplotlib 3.11.2。Git 用于本地提交，GitHub 是远程仓库；今天没有 push。测试使用标准库 unittest，不需要测试框架额外依赖。

在项目根目录运行：

```powershell
conda run --no-capture-output -n agent python run_agent.py
conda run --no-capture-output -n agent python -m unittest discover -s tests -v
conda run --no-capture-output -n agent python -m compileall src tests run_agent.py
git diff --check
```

若 `conda activate agent` 在本机被 PowerShell 激活脚本拦住，以上 conda run 是本次实际使用的替代方式。API Demo 需要本机 `.env` 密钥和网络；单元测试不需要真实 API 或私人数据。

## 十、当前测试情况

最终 **61 项 unittest 全部通过**。原有 32 项 Day 2/3 测试继续通过；Day 4 新增 registry/CSV/列识别/单位/比较/取值/摘要/绘图测试 27 项，另外增加 schema 映射和模型回传路径隐藏测试 2 项。

覆盖未知 alias、非法路径、符号链接偏移、缺文件、缺注册表、非法 JSON、BOM/GBK/分号/制表符、坏 CSV、单位歧义、nearest/linear、重复时间、非有限数值和没有 crossing 等边界。新增测试用合成 fixture 与临时注册表，不能依赖用户目录恰好存在。

编译检查和 `git diff --check` 通过。八个实际 DeepSeek CLI Demo 覆盖列表、inspect、真实比较、100 ps、真实绘图、合成比较、乘法和概念问答。

如实记录：首轮合成 Demo 曾把仓库文件名传给外部工具，被拒绝后恢复；收紧说明后单独复测正确使用 Day 3 工具。初轮真实 inspect 的回答也曾误说两条采样点数不同，而工具元数据明明各为 101 行；已加入更明确的约束。测试通过不等于自然语言永远无误，复核时应优先看工具结构化结果。

## 十一、Git 历史

以下 hash 均来自本地实际 `git log`：

| 阶段 | Commit | 内容 |
| --- | --- | --- |
| Day 1 | 0b724a0 | feat: 初始化 Physics Research Agent 项目 |
| Day 2 | 1fa7651 | feat: 实现 Tool Calling 与基础 Agent 循环 |
| Day 3 | 618419f | feat: 增加科研 CSV 分析与微磁学数据工具 |
| Day 4 实现 | 4934e17 | feat: 接入本地真实微磁学数据分析 |

本文在实现提交完成后写入准确 Day 4 hash，再单独提交为 `docs: 总结 Day 1 至 Day 4 学习进展`。它引用实现版本，而不嵌入自身提交 hash；若把文件自己的 hash 写回并 amend，hash 会再次变化。

本次交付有两个本地 Day 4 提交，main 相对当前 origin/main 超前 2 个，无落后项。没有 push、repo sync、reset 或 rebase；远程分支引用未修改。用户自行决定何时推送。

## 十二、项目安全设计

`.env`、`config/data_sources.local.json` 被忽略；`data/local/` 与 `outputs/` 只保留 `.gitkeep` 的公开占位。真实源留在原位置，不批量复制到仓库，不修改、重命名或移动。

外部工具只接受被注册的 alias，拒绝模型任意路径；注册文件限定绝对 CSV，并检查解析后的路径偏移。输出名白名单限制 PNG 目录；calculator 不提供任意代码执行。

提交前检查 status、diff、暂存区、忽略规则和敏感内容。公开数据只有 synthetic 示例与 fixture；API Key、本地注册表、真实 CSV、真实科研 PNG 都未提交。四份源文件哈希前后不变，是本次只读检查的证据。

**Git 隔离不等于离线保密。** DeepSeek 仍会收到必要的结构摘要、少量预览和计算结果；自动路径隐藏不是全面脱敏，用户需确认未发表内容是否允许发送。当前只是本机单用户小项目，不是生产级权限体系。

## 十三、当前项目不足

- 没有 RAG、论文阅读、向量检索、Web UI 或跨问题记忆。
- Loop 简单、最多五轮；没有生产级网络重试、流式交互、预算管理和审计机制。
- Schema 手写，模型可能选错工具或解释错误，不能只相信流畅的回答。
- 适配支持普通单表 CSV 和简单 `# ` 表头；复杂多级标题、单位行、未知列名需显式指定或后续针对性适配。
- 组合为单层成员，比较恰好两条曲线，不能自动理解任意研究项目或运行模拟软件。
- 插值不提供置信区间，也没有网格收敛、物理误差或因果机制分析。
- 本地 registry、路径限制、脱敏不是多人/服务器级安全隔离。

因此准确定位是“已验证的小型科研数据 Agent 原型”，不是自主科研系统或生产级服务。

## 十四、如果我要面试

下面是约三分钟的介绍稿，描述项目事实，不冒充所有代码都独立完成：

“我是一名物理本科生，想把自己的科研数据背景和 LLM 应用结合起来，所以在 Codex 协助下做了 Physics Research Agent。我选择了小型 CLI，而不是一开始上复杂框架，因为我想先理解模型、工具和数据之间真实发生了什么。

第一天我从 API 请求和响应开始。第二天接入计算器和电子能量工具；模型只输出工具名和参数，真正计算的是 Python，再把结果通过 call_id 对应回传。这解决了‘模型看起来在算，但没有可靠执行’的问题。

第三天接入 pandas 和 matplotlib，用合成磁化曲线验证 inspect、过零时间和绘图。过零定义是首次负到正 crossing，时间由相邻点线性插值得到。我也检查 NaN、重复时间、非法路径等边界。

第四天转向真实数据。难点是文件名字像对比曲线，却实际是三行汇总表。我没有假装从汇总表复现计算，而是追溯两份原始 MuMax3/COMSOL 曲线，注册到本地 alias，再统一 time/mz/source。两条曲线各 101 点但时间网格不同，所以保留原生采样再分别计算。

真实复算得到约 73.838 和 72.819 ps，与现有汇总一致；100 ps 的 mz 也一致。真实曲线图实际生成，最终 61 项测试通过。原文件只读，配置、密钥、真实 CSV 和 PNG 不提交。

这个原型也暴露了模型会选错工具和解释错误的问题，所以我区分工具数值与自然语言解释。我下一步会先巩固代码、做固定验收题，再考虑有授权资料的最小 RAG；目前不把它说成生产级自主科研系统。”

## 十五、可能的面试问题

### 1. Tool Calling 是什么？

模型输出工具名和结构化参数，程序实际执行对应函数。结果再交回模型，它可以继续调用或生成回答；不是让模型直接运行本机代码。

### 2. 为什么不直接让 LLM 算数？

语言生成不保证严格数值计算，也不证明它读取过当前文件。交给可测试的 Python 算法才能追溯输入、方法和结果。

### 3. Agent Loop 是什么？

是“请求模型、执行工具、回传结果”的循环。模型不再请求工具时返回文本；错误也可以回传帮助修正。

### 4. 为什么要 MAX_STEPS？

避免模型反复调用工具造成无限循环和成本失控。本项目设为五轮，是简单保护，不是完整的预算管理。

### 5. 为什么不用 eval？

任意 eval 会把输入作为代码执行，可能越权。计算器用 AST 白名单只接受明确支持的运算与函数，仍需要数值边界保护。

### 6. 怎样防止路径穿越？

仓库工具限定目录并检查 resolve 后的路径，拒绝 `..` 和任意绝对路径。外部工具只接收 alias，从用户登记的 CSV 精确定位，并拒绝最终路径偏移。

### 7. 为什么真实数据不进 Git？

它可能是私人或未发表研究资料，Git 历史又难清理。公开仓库保留代码和合成测试，真实文件只在用户授权的本机位置读取。

### 8. Switching time 怎么定义？

本项目取 mz 首次从负值达到或穿过零的时间。它不同于最终达到 +1，也不等同于临界电流判据。

### 9. 为什么用线性插值？

离散采样通常没有恰好 mz=0 的点，因此在包围零点的两个采样之间估算时间。不能把输出的很多小数位理解为模拟具备同样物理精度。

### 10. DataFrame 是什么？

它是 pandas 的二维带标签数据结构，可按列操作、查看类型和缺失值。这里用它承接 CSV，再将选定列转为有限数值。

### 11. 为什么需要 adapter？

不同文件的列名、编码和时间单位不同，直接套用固定列会失败。适配层统一到 time/mz/source，后续算法可以共用，但不能悄悄重采样。

### 12. 模型选错工具怎么办？

后端不能因为模型请求就放宽授权；先校验并回传错误。用真实 Demo 找到歧义后改进 schema/instructions，再复测，但不能宣称以后必然不出错。

### 13. 工具失败怎么办？

返回清楚的错误，不能编一个结果。当前覆盖参数和文件操作错误，网络故障处理还很基础，生产环境需要更完整的重试与观测。

### 14. 怎么证明结果可信？

先用已知 synthetic fixture 验证算法，再做 Day 2/3 回归，最后用当前真实原曲线复算并核对既有汇总。还要检查单位、插值区间、图和源文件哈希，而不是只看模型回答。

### 15. 下一步怎样扩展 RAG？

先选择一份允许读取和发送的资料，定义能核对出处的小问题集。检索得到证据再生成回答；RAG 不应替代数值工具，也不自动解决科研隐私。

### 16. 单位 unknown 时能不能默认 ps？

不能，数量级错误会让比较毫无意义。应要求用户确认单位；已知单位可转换，未知单位的显式声明则是用户提供的信息。

### 17. Nearest 与 linear 有什么区别？

nearest 取最近的已有点，linear 用包围目标的两点插值。目标正好是原始采样时间时直接取原值，两种方式都不需要插值；本项目禁止外推。

### 18. 同样 101 行为什么仍要保留各自时间？

点数相同并不代表时间坐标相同，本次 MuMax3 有非整数 ps 点。不能凭行号一一相减或强行套共同时间，应按各自真实坐标计算。

## 十六、Day 5 建议

优先亲自消化当前项目：运行 CLI，阅读 `run_agent`、`find_zero_crossing` 和 registry 查找，手算两个点的零点。独立修改一份 synthetic fixture，解释哪个测试应失败、为什么；这是比立即堆框架更具体的学习验收。

然后建立小而固定的验收问题集，区分工具路由是否正确、数值是否正确、解释是否越界。重点覆盖本次出现的“仓库 CSV 与外部 alias 混淆”以及“点数与网格混淆”，不要只以回答自然就判通过。

若上述能自己解释，再考虑一份授权公开物理资料的最小检索引用原型，明确出处与拒答条件。先确认资料与网络发送边界，再决定是否做 RAG；目前没有需要引入多 Agent、Web UI 或复杂记忆的依据。
