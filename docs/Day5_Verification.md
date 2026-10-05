# Day 5 验收记录

日期：2026-10-05。范围：本地字符级 TF-IDF RAG、实际行号引用、证据不足拒答及与 Day 2–4 数值工具分流。没有 embedding API、向量数据库、网络搜索、PDF pipeline、Web UI 或多 Agent；没有 push。

## 环境与实现参数

- Python 3.12.14，Conda agent，scikit-learn 1.9.1，已将实际版本加到 requirements。
- 普通 conda activate 后仍指向 Python 3.8，实际开发/测试统一 conda run -n agent。
- 首次安装在沙箱中触发拒绝访问，随后获准明确安装到 agent 环境，import/version 验证成功。
- 9 documents / 112 chunks；下面六份 Day 2–4 docs、Day5_RAG_and_Citations、knowledge/public/README、项目 README。
- 六份既有 docs：Day2_Tool_Calling、Day3_Scientific_Data_Tools、Day3_Verification、Day4_Real_Scientific_Data、Day4_Real_Data_Validation、Day1-4_学习总结。
- 本轮 Day5_Verification 与 Day1-5 总结不索引，避免把验收问题/答案当自身独立证据。tests/fixtures 和评估 JSON 也不进入 corpus。
- 按 Markdown 标题分节、完整行累计约 900 字符、节内约 150 字符 overlap；标题层级独立保存，引用行号来自原文。超长单行/整行重叠可超过目标长度。
- TfidfVectorizer：analyzer=char、ngram_range=(2,4)，默认归一化，cosine similarity 排序，top_k 默认 4、范围 1–8，每 source 最多 2 个片段。
- cosine threshold=0.05，查询 n-gram 词表覆盖率要求至少 0.50。只去掉少量通用问句壳，不按研究主题硬编码答案或 Agent 路由。
- 小知识库每次工具调用重建，无持久数据库。引用格式 `[source:Lstart-Lend]`；chunk_id 同样包含 source 和实际行范围。

## 固定检索评估

执行 `python scripts/evaluate_rag.py`，12 cases：8 正例、4 负例。

| 指标 | 实际结果 |
| --- | --- |
| 正例 expected source 进入 top-4 | 8/8 |
| Recall@4 / 来源命中率 | 1.0 |
| 负例 found=false | 4/4 |
| 负例拒绝率 | 1.0 |

正例检查 Tool Calling 执行者、eval 安全、过零计算、Git 私有数据、Day 4 实数、101 行/时间网格区别、当前 RAG 状态、软件精度结论。负例覆盖量子霍尔的两种问法、GPT-6 训练参数、歌剧话题。

这里每道正例定义一个可接受 source 集合，命中任一个记成功；所以本质是题级 source Hit@4，不是对所有相关片段的完整召回。12 题用于开发调参，没有独立 holdout；不能报告成“LLM 答案准确率 100%”。

首轮 threshold=0.12、没有层级标题/覆盖率保护时，只命中 4/7 正例，拒绝 1/3 负例。通用“是什么”词抬高弱匹配；继而增加标题层级、有限 source 去重、通用问句壳清理和覆盖率检查。一个 101 行问题在 Day 4 文档的相关段得分约 0.05，当前阈值因此校准为 0.05。另补 eval 正例与短问法负例，最终保持 12 题全通过，而非把不通过的题删掉。

## 真实 Agent CLI Demo

通过 `run_agent.py` 两轮实际请求 DeepSeek；不是用 mock 冒充真实模型。MAX_STEPS 仍为 5。

| Demo | 实际路由及结果 |
| --- | --- |
| 1 文档中的 Python 执行者 | search_knowledge_base；本地 Python 程序，不是模型；包含真实 Day2 L44-L70 引用 |
| 2 switching time 原理 | RAG；首个负到正区间、线性插值；实际 Day3 L19-L32 和 Day4 L51-L62 引用 |
| 3 Day 4 历史值与精度 | RAG；73.83834774284676 / 72.81911124409665 ps；明确不能证明 COMSOL 更准确，引用真实验收段 L23-L43 |
| 4 量子霍尔文档题 | RAG 返回证据不足；最终明确拒答，没有常识伪装成文档内容 |
| 5 当前 CSV 重算 | list/inspect → compare_switching_times；当前文件数值，不调用 RAG 替代 |
| 6 当前 100 ps | inspect → 两次 sample_value_at_time；0.9564934 / 0.962276697685，均精确采样点、无插值 |
| 7 12345 × 6789 | calculator，83810205 |
| 8 蓝天原因 | 直接解释瑞利散射，没有 RAG 或 Python 调用 |

Demo 1–3 的最终答案均通过“本轮检索引用集合”校验，没有未检索引用被接受。真实值与 Day 4 保持一致；Day 5 不改 crossing 判据或模拟原文件。

如实记录自然语言问题：初轮曾误读 sorted=false 为“未排序”，并从采样差异推断时间差成因。已给采样/摘要工具补 sorting_note，强化 instructions；复测正确解释无需重新排序，且不再把采样差异作为时间差原因。复测 Demo 5 仍曾额外报出约 1.4%，不是工具返回的百分比；已进一步收紧规则并追加复测。引用校验只校验来源身份，不自动检查全部派生数字和每句话的证据蕴含，不能承诺模型永不越界。

追加 Demo 5 复测已直接给出完整 Python 过零结果与差值，没有再给百分比，正确解释 sorted=false 为无需重排；仍可能补充未经工具单独计算的约数说明，应人工复核。Demo 3 也会补充一般性的精度研究建议；应区分文档所支持的结论与模型建议，不能把未见某项记录说成现实中不存在。普通蓝天答案可能自行加入数值例子，但没有为概念题额外调用工具。

## 独立 Retriever CLI

实际运行 `run_rag.py`：Tool Calling 问题 Rank 1 命中 `[docs/Day2_Tool_Calling.md:L44-L70]`，分数约 0.275；显示 heading、片段、source 行范围。短问“量子霍尔效应是什么？”输出没有足够相关证据，top_score=0.0。它没有调用 DeepSeek，直接展示 retrieval 与 generation 是不同步骤。

README/学习文档最后补充时 chunk 数由 113 变为 112，已重新执行固定评估和全套测试，以最终 112 为准。

## 自动测试与安全

79 项 unittest 全通过：保留 Day 2–4 的 61 项，新增 15 项 RAG 与 3 项 Agent 引用/拒答测试。覆盖允许目录、真实相对路径、行号、重叠、中文查询、负例、top_k、伪造/缺失引用、路径逃逸、配置/CSV 排除和注入 fixture。

malicious_document 只是测试文本，loader 不对文档 exec/eval/subprocess。context 明确标 UNTRUSTED DATA，转义闭合标签；不授予文档额外能力。这是基础防护，不是完整安全证明。

compileall（src/tests/scripts/run_agent/run_rag）和 git diff --check 通过。提交前检查暂存区、忽略规则和私密内容，不输出真实密钥。`.env`、API Key、本地 registry、真实 CSV/PNG、knowledge/local 私人资料均未提交；本轮 corpus 只有公开项目文档，local 只保留 `.gitkeep`。

Git 忽略不等于 API 看不到数据：将来用户主动放进 knowledge/local 的片段一旦命中，就可能发送到 DeepSeek，必须事先确认授权。

本次只做本地 commit，推送由用户自行决定。代码状态、实际 hash 和 ahead 数以最终 `git log` / `git status -sb` 为准。
