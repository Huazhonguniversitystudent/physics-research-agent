# Day 7：Portfolio 与独立 Evaluation

## 1. 为什么“有功能”不等于“有作品”

功能只回答“代码能不能跑”。作品还要让陌生人快速理解问题、设计、证据、运行方式、安全边界和失败案例。一个只有源码、没有入口和验证说明的仓库，很难让面试官在几十秒内判断价值。

## 2. 为什么 Web Demo 有价值

CLI 适合开发者，但 Web 能把输入、答案、Tool Trace、数值和 citation 放在同一画面。它不是为了把算法包装得更复杂，而是降低演示成本，让“模型不是直接猜的”可见。

## 3. 为什么 public/private mode 分开

求职 Demo 的观众与本地科研使用者权限不同。Public Mode 应只接触可以公开展示的 synthetic、公开文档和公开论文；Private Mode 才允许用户主动授权本地 registry。模式分离把默认权限设为最小值。

## 4. 为什么 Web 不能默认加载私人科研数据

浏览器输入是开放入口。如果它能触发 registry、真实 CSV 或私人论文，演示中的一句自然语言就可能访问未发表数据。仅隐藏前端按钮不够，后端还必须收窄 tool schema、验证参数并固定公开数据路径。

## 5. 什么是 holdout

Holdout 是在开发规则确定后才用于评估的一组未参与调参的问题。本项目把 Day 5/6 的开发题与 Day 7 的 16 题 holdout 分开，并在正式运行前保存 SHA-256。

## 6. 为什么不能用 holdout 调参

一旦看到失败就反复改阈值、问题或预期页码，holdout 就变成新的 dev set，结果会高估泛化能力。正确做法是保留失败、分析原因；未来改进使用新的开发题，必要时再建立新的最终测试集。

## 7. Dev set 与 holdout 的区别

Dev set 用来比较方案、调阈值和修规则，可以反复运行。Holdout 用来测量当前方案对未见表达的表现，应限制查看和运行次数。Day 5 dev set 的 8/8、4/4 不能与 Day 7 holdout 的 Docs 2/4、Negative 1/4互相替代。

## 8. Routing evaluation 是什么

Routing 检查模型是否选择正确的工具家族：普通回答、calculator、project_docs 或 papers。它不验证工具结果或最终措辞。本次 4/4 说明这四个样例选路正确，不说明所有自然语言问题都能正确路由。

## 9. Retrieval evaluation 是什么

Retrieval 检查期望来源或页码是否进入 Top-K。Project Docs 用 source Hit@4，PDF 用 Page Hit@4。命中只表示证据候选出现，不表示模型一定正确使用；未命中也只能说明当前检索没有返回足够证据。

## 10. Final answer grounding 是什么

Grounding 审查答案的核心主张是否被返回证据支持。本项目人工标注 8 个生成回答为 Supported、Partially Supported 或 Unsupported。它比引用格式检查更接近“回答是否有根据”，但样本小且只有一名标注者。

## 11. Unit test 与 AI evaluation 的区别

单元测试适合确定性函数：路径拒绝、插值、页码、引用集合、Public Mode。LLM 的路由和表述会随输入与模型变化，需要固定问题、分项指标和人工审阅。113 个单测通过不能替代模型评估。

## 12. 为什么失败结果也应该展示

失败定义了系统边界，也为下一步学习提供方向。本次 Docs 2/4 和 Negative 1/4 比“全部成功”的宣传更有价值：它真实揭示 char n-gram 对改写和 hard negative 的不足。

## 13. 为什么 105/113 个测试不等于模型可靠

Day 6 有 105 项、Day 7 增至 113 项，它们大多不访问真实 API，而是验证确定性代码和 mock 交互。它们能防回归，不能证明 DeepSeek 永不选错工具、永不扩写、永不误解证据，也不能覆盖全部物理问题。

## 14. 为什么 GitHub README 很重要

README 是项目的入口和边界说明。面试官需要快速看到：做了什么、为什么做、如何运行、有哪些证据、哪里失败、哪些数据不公开。它也是防止自己在简历中夸大项目的约束清单。

## 15. 如何诚实讲 AI-assisted development

可以说：“开发中大量使用 Codex 作为编码助手，但我持续参与需求拆解、物理数据背景和验收。我不声称所有代码都能从零默写；我用运行、核心代码阅读、fixture 修改、失败分析和现场解释来证明理解。”诚实不削弱项目，掩盖才会在追问时失去可信度。

## Day 7 我真正应该理解的 5 件事

1. **默认权限最小化**：Public Mode 不是标签，而是 schema、参数、路径和语料的后端边界。
2. **评估必须分层**：unit test、routing、retrieval、citation validity、grounding 不能混成一个数字。
3. **Holdout 纪律**：看到失败后不调参，哈希与一次正式运行让结果可追溯。
4. **引用不是证明**：引用身份正确仍可能语义不支持，必须核对 claim entailment。
5. **作品需要可解释性**：能演示、能复现、能讲失败、能说明 AI 协助，比继续堆框架更重要。
