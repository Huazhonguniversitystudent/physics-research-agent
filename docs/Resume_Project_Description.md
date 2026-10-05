# Physics Research Agent 简历项目描述

## 中文版本

### 版本 A：一句话

设计并实现面向物理科研的可验证 AI Agent 原型，支持受限 Tool Calling、科研 CSV 分析及带行号/页码引用的 Markdown/PDF RAG。

### 版本 B：三条 bullet（推荐）

- 基于 DeepSeek Responses API 实现 Tool Calling 与五步 Agent Loop，由 Python 受限工具完成数学、物理量及科研 CSV 的可靠计算。
- 适配授权 MuMax3/COMSOL 曲线并以 alias 隔离本机路径；实现首次过零线性插值、单位处理、绘图及 public/private 数据边界。
- 构建字符级 TF-IDF Markdown/PDF RAG 与引用校验，完成 113 项单测及独立 holdout；如实记录 hard negative 与改写检索失败。

### 版本 C：详细版

设计并实现 Physics Research Agent 学习原型，将 LLM 决策、Python 数值执行与 RAG 证据检索拆分。项目基于 DeepSeek Responses API 实现受限 Tool Calling 和最多五轮的 Agent Loop，使用 pandas/matplotlib 分析合成与授权科研 CSV，通过本地 alias registry 隔离绝对路径，并对 MuMax3/COMSOL 磁化曲线执行结构检查、首次过零线性插值和可视化。

在检索侧，使用 char 2–4 gram TF-IDF 建立透明 baseline：Markdown 返回真实行号，PyMuPDF 论文解析返回真实页码，后端拒绝未在本轮检索集合中的 citation。Streamlit Web Demo 默认 Public Mode，只开放 synthetic 数据、公开文档和公开论文。测试包含 113 项 unittest、开发检索集、PDF 固定评估与 16 题独立 holdout；结果分项报告，不把检索命中、引用有效和最终答案 grounding 混成一个准确率。

项目由用户参与需求、物理背景和验收，并在 Codex 协助下完成大量编码与文档。面试时应主动说明 AI-assisted development，不声称全部代码可独立从零手写。

## English Version

### Version A: One-liner

Built a verifiable Physics Research Agent prototype with constrained tool calling, scientific CSV analysis, and grounded Markdown/PDF RAG with line- and page-level citations.

### Version B: Three bullets

- Implemented a five-step agent loop on the DeepSeek Responses API, delegating deterministic math, physics, and CSV operations to constrained local Python tools.
- Adapted authorized MuMax3/COMSOL curves through alias-based path isolation, with schema inspection, zero-crossing interpolation, unit handling, plotting, and public/private data boundaries.
- Built a transparent char n-gram TF-IDF pipeline for Markdown and PDF RAG, added citation validation, and verified the system with 113 unit tests plus a frozen holdout that preserves retrieval failures.

### Version C: Detailed

Designed and implemented a learning-oriented Physics Research Agent that separates LLM decisions, deterministic Python execution, and evidence retrieval. The system uses the DeepSeek Responses API for constrained tool calling, analyzes synthetic and authorized scientific CSV files with pandas and matplotlib, and protects local file locations through an alias registry.

For grounded answers, it shares a character n-gram TF-IDF retriever across Markdown and text-based PDFs. Markdown evidence includes real line ranges, PDF evidence includes physical page numbers, and the backend rejects citations not returned in the current retrieval step. A Streamlit demo runs in Public Mode by default and only exposes synthetic data, public project documents, and a public Mumax3 paper. Evaluation is reported honestly across 113 unit tests, development retrieval sets, a fixed PDF set, and a 16-case frozen holdout rather than presenting a single inflated accuracy number.

Development was AI-assisted with Codex; the user remained involved in requirements, physics context, and acceptance. This should be disclosed honestly in interviews.

## 使用提醒

- 不写“独立开发”“生产落地”“百万用户”“99% 准确率”或“大模型训练”。
- 简历优先使用版本 B；平台项目经历可使用版本 C 的前两段。
- 面试时准备现场解释 `run_agent`、过零插值、scope、citation 校验与 holdout 失败。
