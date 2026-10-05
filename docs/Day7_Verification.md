# Day 7 验收记录

验收日期：2026-10-05。范围：Streamlit Public Demo、独立 holdout、作品集文档、浏览器实测、自动测试与本地提交。没有执行 push、repo sync、reset、rebase 或 force push。

## 环境

- 普通 `python --version`：3.8.13，仍不是目标环境。
- 实际使用解释器：`%USERPROFILE%\miniconda3\envs\agent\python.exe`，Python 3.12.14。
- Streamlit：1.65.0，已按实际版本写入 `requirements.txt`。
- DeepSeek：`deepseek-flash`，Responses API，Key 只由 server 端 `.env` 读取。
- 安装 Streamlit 后，本机 Conda 可执行文件出现“无效的系统 DLL 重定位 / The system cannot execute the specified program”；未擅自修复 Conda，后续统一直接调用 agent 环境解释器。

## Public Demo Mode

默认 `PHYSICS_AGENT_PUBLIC_DEMO` 未设置时为 true。公开模式采用三层限制：

1. 模型只收到公开工具 schema，private registry 工具不出现。
2. Python 执行前再次校验工具名、scope 与数据集，并把 synthetic 数据规范化到固定 `data/examples/synthetic_micromagnetics.csv`。
3. Markdown/PDF loader 使用 `include_local=False`，排除 `knowledge/local` 与本地私人论文。

页面不列出私人 alias。trace 会隐藏 API Key、token、secret、password、authorization 和常见绝对路径，并截断大结果。只有用户明确设置 `PHYSICS_AGENT_PUBLIC_DEMO=0` 才能在本地接入原有 private 工具。

## Streamlit 启动与浏览器验证

实际命令使用 agent Python 的 `-m streamlit run web_app.py`。服务成功监听 `127.0.0.1:8501`，无 import error 或启动异常。

Playwright 首次在受限沙箱内启动 Edge 时因浏览器进程/网络隔离失败；获准在本机环境启动 Streamlit 与 Edge 后成功访问。首次工具轨迹检查发现标量传给 `st.json` 会触发 React 控制台错误，最小改为 `st.code` 后重新运行 calculator 与 PDF Demo，最终控制台 **0 error / 0 warning**。

三张真实截图：

- `docs/images/web_home.png`
- `docs/images/web_tool_calling.png`
- `docs/images/web_pdf_rag.png`

全部只含 synthetic、公开文档和公开论文内容。

## Web 五个示例的实际结果

| 示例 | 实际路由 / 结果 |
| --- | --- |
| 天为什么是蓝色的？ | 普通 LLM 概念回答，无工具；解释瑞利散射 |
| 12345 × 6789 | `calculator`；得到 83,810,205；trace 可展开 |
| 比较 synthetic switching time | CSV tools；约 73.7987 / 72.5994 ps，差 1.1994 ps；明确 SYNTHETIC |
| Tool Calling 谁执行 Python | `search_knowledge_base(scope=project_docs)`；回答本地 Python，引用 Day 2 L44-L70 等 |
| Mumax3 默认动力学积分 | papers RAG；回答 RK45 Dormand–Prince，引用 `[paper:mumax3:p12]` |

模式 B 的无 API 路径也实际点击：显示 73.799 ps、72.599 ps、1.199 ps 与曲线图。模式 C 已实现显示公开论文 title、五位 authors、2014、paper_id 与 arXiv source；public-only metadata 单测通过。

## Holdout 纪律

- 文件：`tests/holdout_eval_cases.json`
- 题数：16（Routing/Docs/PDF/Negative 各 4）
- SHA-256：`1b235726c32510aa2501760c141e293e7ba9a371c5a9867322837c7a42d6ea3a`
- 正式评估：只运行一次，未 crash，未重跑。
- 正式运行后没有修改题集、阈值、检索规则或 acceptable pages。
- README 和求职文档在正式 run 后完成，因此结果明确视为正式 run 时的语料快照，不重跑追求更高数字。

## Holdout 结果

| 指标 | 结果 |
| --- | ---: |
| Routing | 4/4 = 100% |
| Project Docs source Hit@4 | 2/4 = 50% |
| PDF Page Hit@4 | 4/4 = 100% |
| Negative rejection | 1/4 = 25% |
| Generated answer citation validity | 7/8 = 87.5% |
| Manual grounding | Supported 5 / Partially Supported 2 / Unsupported 1 |

Docs 的 alias/page-boundary 改写直接检索失败；三个 hard negative 因技术词字面重合误召回。一个 page-boundary 生成答案因没有正确引用被后端拒绝。详细逐题记录见 `docs/Day7_Holdout_Evaluation.md`。

## 自动测试与代码检查

- `python -m unittest discover -s tests -v`：**113/113 通过**。
- Day 2–6 的 105 项回归全部保留；新增 8 项 Web/Public Mode 测试。
- `python -m compileall src tests scripts run_agent.py run_rag.py run_pdf_rag.py web_app.py`：通过。
- `git diff --check`：通过；仅有 Windows LF/CRLF 提示，不是 whitespace error。

第一次全量测试在 Windows 沙箱系统 Temp 下出现 `PermissionError`；将 `TEMP/TMP` 指向仓库已忽略的 `outputs/test-tmp` 后，不改测试逻辑即 113 项全通过。该次不是代码测试失败，最终有效结果以上述运行准。

## 安全检查

自动测试确认：Public Mode 默认 true、private tool schema 不暴露且后端拒绝、synthetic 固定路径、local 文档/PDF 排除、Key 不进 trace、私人路径被隐藏。

`git check-ignore` 确认下列路径规则有效：

- `.env`
- `config/data_sources.local.json`
- `data/local/*.csv`
- `outputs/*`
- `knowledge/local/*`
- `knowledge/local/papers/*.pdf`
- `knowledge/public/papers/*.pdf`

提交候选文本的 Key 模式扫描为 0。tracked files 检查未发现 `.env`、private registry、真实科研 CSV/PNG、private PDF 或第三方论文 PDF 本体。

## Git

- Day 7 功能 commit：`e6d5fcf feat: 增加公开安全 Web Demo 与独立评估`。
- README 与求职材料使用第二个本地 documentation commit；其 hash 以最终 `git log` 为准，避免在提交自身内容中制造自引用 hash。
- 全程没有执行 `git push`。用户手动推送。

## 诚实边界

项目仍是单机学习原型：无 OCR、embedding、向量数据库、长期记忆、登录、数据库、云部署和生产级防注入。TF-IDF 的 paraphrase/hard-negative 弱点已被 holdout 量化；citation identity 不等于 claim entailment；113 项单测不等于模型可靠。
