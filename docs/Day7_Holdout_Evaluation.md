# Day 7 独立 Holdout Evaluation

评估日期：2026-10-05。题集在正式执行前固定，随后计算 SHA-256，并只进行一次正式运行。没有根据结果修改阈值、检索规则、硬编码关键词、问题文本或可接受页码。

## 固定题集

- 文件：`tests/holdout_eval_cases.json`
- 题数：16
- SHA-256：`1b235726c32510aa2501760c141e293e7ba9a371c5a9867322837c7a42d6ea3a`
- 分类：Routing 4、Project Docs 4、PDF 4、Negative 4
- 正式命令：`python scripts/evaluate_holdout.py`
- 机器可读报告：`outputs/day7_holdout_report.json`（本地忽略，不提交）

PDF 正例是在实际阅读 Mumax3 论文 p10、p11、p17、p19 后设计，没有复用开发集的 FD p2 或默认 RK45 p12 原句。负例包含英文和中文 hard negative，并刻意保留与知识库有较多字符重合的词。

## 分项结果

| 指标 | 结果 | 解释 |
| --- | ---: | --- |
| Routing | 4/4（100%） | 普通回答、calculator、project_docs、papers 均选对 family |
| Project Docs source Hit@4 | 2/4（50%） | 原始固定问句直接检索；alias 与跨页问题未命中 |
| PDF page Hit@4 | 4/4（100%） | p10、p11、p17、p19 均进入 Top-4 |
| Negative rejection | 1/4（25%） | 三个 hard negative 被字面 TF-IDF 误召回 |
| Generated answer citation validity | 7/8（87.5%） | 1 个答案因缺失 citation 被后端拒绝 |

这些数字不能相加成一个“总准确率”。Routing 是模型选择，Hit@4 是检索排序，negative rejection 是未知主题识别，citation validity 是引用身份检查，它们测量不同环节。

## 检索失败分析

### Project Docs 2/4

`docs_alias_boundary` 与 `docs_page_boundary` 的固定中文问句都得到 `found=false`。主要原因是字符级 TF-IDF 依赖字面重合；问句把原文概念换成“登记表”“页边界重置”等表达后，query coverage 未达到有效检索条件。

这不等于资料中没有答案。实际 Agent 会改写检索词：alias 问题经改写后找到了 `Day4_Real_Scientific_Data.md`，回答得到人工 Supported；页边界问题也召回了正确片段，但模型最终没有原样使用允许引用，后端将答案拒绝。

### Negative 1/4

- 英文“superconducting-qubit coherence time + GTX TITAN”误召回 p20/p1/p19/p18。
- 中文“GPU 性能 + Higgs 质量”被拒绝，正确通过。
- “Tool Calling + Transformer 训练语料”误召回 Day 2/5 文档。
- “Kubernetes service mesh + Agent Loop”误召回 Agent Loop 文档。

这再次表明：英文长文和技术文档中，只要存在大量通用技术字符，低阈值 char n-gram TF-IDF 就可能把局部词重合误当成主题证据。今天不为这四题调阈值，因为 holdout 的职责是暴露问题，不是参与调参。

## 8 个生成回答的人工 Grounding

标注标准：

- **Supported**：核心结论与必要解释均可由返回证据支持。
- **Partially Supported**：核心结论正确，但包含证据没有完整支撑的扩展或过强解释。
- **Unsupported**：没有提供可接受的实质答案，或核心结论不受证据支持。

| Case | 标注 | 人工说明 |
| --- | --- | --- |
| docs_call_id | Supported | `call_id` 与 `function_call_output` 的对应关系受 Day 2/总结证据支持 |
| docs_alias_boundary | Supported | alias、白名单、路径隐藏与边界说明均有返回文档支撑 |
| docs_page_boundary | Unsupported | 检索找到了正确片段，但最终引用校验失败，系统只返回拒绝提示 |
| docs_entailment | Supported | 正确区分 citation identity 与 claim entailment |
| pdf_thermal_solver | Partially Supported | Euler/Heun、力矩连续性和固定步长受 p10/p12 支持；对“高阶方法”的概括略宽 |
| pdf_zhang_li | Partially Supported | “more than one layer of cells”受 p11 支持；将其具体解释成厚度方向略超出原句 |
| pdf_moving_frame | Supported | 平移磁化、跟随畴壁、边缘电荷与新几何受 p17/p18 支持 |
| pdf_grid_performance | Supported | cuFFT、2 的幂/7-smooth、质数惩罚受 p19 支持 |

汇总：**Supported 5 / Partially Supported 2 / Unsupported 1**。

人工标注不是双盲多人标注，也没有计算一致性系数；它是小规模审阅记录，不能包装成通用模型准确率。

## Citation Validity 与 Grounding 的区别

7/8 citation valid 只表示答案中的引用字符串属于该轮检索允许集合。它不验证“这句话是否被该页蕴含”。例如 thermal 和 Zhang-Li 两题的引用身份有效，但人工仍标为 Partially Supported；这正是后端身份校验与人工 grounding 必须分开报告的原因。

## 评估纪律与限制

1. 正式 holdout 只运行一次，输出原样保留。
2. Day 7 README 与求职材料在正式 run 后完成，因此该结果是正式 run 时语料快照；之后文档变化可能改变排名，本轮不重跑来追求更好数字。
3. 题数很小，只包含一篇 PDF；不能代表跨论文、跨语言或生产流量。
4. 模型生成有随机性；Routing 与答案措辞重跑可能变化。
5. 独立于 Day 5/6 开发题，不等于统计意义上充分独立或无人工选择偏差。

最重要的结果不是“PDF 4/4”，而是 holdout 清楚暴露了 project paraphrase 与 hard negative 的弱点。下一步若改用 embedding 或 reranker，应建立新的 dev set 调参，并保留这份 holdout 作为历史快照，而不是改写本次结果。
