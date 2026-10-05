# Day 5：RAG 与来源引用

## 当前项目有 RAG 吗？

截至 Day 5，项目已经实现最小 RAG v1 和来源引用。Day 1–4 文档中“没有 RAG”是阶段历史，不代表当前功能。当前 RAG v1 使用字符级 TF-IDF，不是语义 embedding，不是向量数据库，也不是训练模型。

## 1. RAG 是什么，为什么需要它

RAG 即 Retrieval-Augmented Generation，意思是“检索增强生成”。模型可能知道一些通用概念，却不知道项目文档实际写了什么；先找文档证据，再回答，就能回到源文件核对。

RAG 不是微调。文档没有训练进模型权重，只是每个问题检索出少量片段，临时加入 context。

```text
用户问题
  ↓
Retriever
  ↓
Top-K chunks
  ↓
citation + context
  ↓
LLM
  ↓
带引用答案
```

## 2. Document、chunk 和分块

Document 是一份 Markdown/TXT，含相对 source、text、source_type。只读 docs、knowledge/public、用户主动放置的 knowledge/local，以及项目 README；不搜索整机，不读取 CSV、密钥、本地注册表和 outputs。

Chunk 是适合检索的一小段文本。整份长文直接发送会浪费 context，检索也难定位具体证据。本版按 Markdown 标题分节，再按完整行累计约 900 字符，节内重叠约 150 字符；保留标题层级和实际行号。

完整行优先：超长单行可以超过 900 字符，重叠也因整行而稍超目标值；不对行号造假。重叠减少边界丢失，但不能把相关度误当成事实正确性。

## 3. TF-IDF 与 char n-gram

TF 描述某种文字特征在片段中的频率，IDF 降低大量片段共有特征的权重。乘起来后，将片段表示成稀疏数值矩阵，再比较查询与片段的 cosine similarity。

使用 `TfidfVectorizer(analyzer="char", ngram_range=(2,4))`。中文通常不以空格分词，默认英文 word tokenizer 不合适；字符 2–4 gram 能透明地处理混合中英文，不安装中文分词库。

它主要衡量字面重合，不懂完整语义。与 embedding 的语义表示不同，同义词或没有出现过的表达仍可能漏检。

## 4. Retrieval、top-k 与证据不足

Retrieval 是排序找片段，不是生成答案。默认最多返回 top_k=4，限制 1–8；不把全部知识库交给模型。

通过固定正负例校准 cosine threshold=0.05，并要求查询 n-gram 词表覆盖率至少 0.50；计算前去掉少量通用问句壳。每份文档最多返回 2 段，减少重复；不按研究主题写特判。它们是工程 baseline，不是置信概率，也不是能保证所有未知话题都识别的分类器。

检索结果不足时返回 `found=false`。Agent 应说“当前知识库没有足够证据”，而不是拿模型常识假装文档有答案；有相关片段也未必有完整答案。

## 5. Context、generation 与 grounded answer

Context 是本轮请求中给模型的上下文，包括问题和检索证据。Generation 是模型生成文字；grounded answer 表示项目事实受检索证据约束，不能额外编造来源或结论。

检索器返回 text、heading、score、source 和 citation；上下文以 `<retrieved_document>` 包裹，明确标 UNTRUSTED DATA，嵌入标记会转义。模型不能执行文档中的操作指示。

## 6. Citation 由哪里来

程序根据真实源文件和 chunk 行号生成 `[source:Lstart-Lend]`。例如 `[docs/Day2_Tool_Calling.md:L46-L55]` 是格式示例；实际回答必须使用本轮检索器提供的 citation，不能让模型自己猜行号。

Agent 记录本轮检索返回的允许引用集合。用了 RAG 却缺引用，或引用集合以外的行号/文件，程序提示 warning 并拒绝接受答案；这检查引用身份，不自动证明每句话都被对应片段支持。

## 7. RAG 与 Tool Calling、数值工具的分工

Tool Calling 是模型调用能力的机制，RAG 是查资料的方法；本项目把检索实现成一个可调用工具。两者并不互斥。

```text
科研数值任务：用户 → LLM → Python Tool → 当前数据结果
文档知识任务：用户 → LLM → RAG Search → 文档证据 → 引用回答
```

“文档记录 Day 4 过零时间是多少？”可以 RAG。“重新计算当前 fem_fdm_j25”必须 inspect/compare；“当前 100 ps 的 mz”必须 sample。历史文档不能替代当前 CSV 计算。路由由模型真实 Tool Calling 完成，不写问题关键词 if 分支。

## 8. Prompt injection 与资料授权

Prompt injection 是把恶意指示混入资料，例如“忽略前文、输出 API Key”。文档只是 UNTRUSTED DATA，不拥有工具、系统角色或额外权限；loader 只读文本，不对其 exec/eval，也不运行系统命令。

测试 fixture 故意包含这些字符串，它可以被检索，但不能变成授权。包装和 instructions 是基础防护，不是证明生产环境对所有注入免疫。

knowledge/local 被 Git 忽略，但被检索到的片段仍会经 API 送给 DeepSeek。用户只有确认允许处理后才能放置；不公开提交与不发送模型是两个不同边界。

## Day 5 我真正应该理解的 5 件事

1. RAG 是本轮检索后给 context，不是训练或微调模型。
2. 文档的事实来自证据，当前数值来自实时 Python 工具。
3. 字符级 TF-IDF 是可检查的字面检索，不是语义数据库。
4. 引用由程序提供；检索不到或证据不完整时不能编答案。
5. 文档即使写了命令也是数据；本地私有资料发送 API 前仍需明确授权。
