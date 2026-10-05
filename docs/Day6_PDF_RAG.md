# Day 6：PDF 论文 RAG 与页码引用

## 今天解决什么

让本地程序读取一份公开物理论文，找到与问题相关的页内文本，再把证据交给 DeepSeek。它不是自动下载论文、OCR、模型训练或新的检索算法。

## 1. PDF 和 Markdown 有什么区别

Markdown 是有顺序、标题与行号的文本。PDF 更像固定版面的页面：文本、图像、字形、位置分别存储。看到的段落不一定等于内部阅读顺序，两栏和公式尤其容易错序。

## 2. 为什么 PDF 比 TXT 难解析

TXT 直接读字符串；PDF 需要解析页面对象和文字绘制信息。有的 PDF 只包含扫描图片，肉眼看到字，但没有可复制的文字层。数字、上下标、连字符和图中标注也可能提取成零散行。

## 3. PyMuPDF 做什么

PyMuPDF 是读取、渲染和创建 PDF 的 Python 库。本项目只新增这一个依赖，使用 `import pymupdf`，与传统 `import fitz` 对应同一个库，不额外安装名为 fitz 的其他包。

## 4. page object 是什么

`with pymupdf.open(path) as document` 打开文档；遍历 document 得到每页的 page 对象。`page.get_text("text")` 请求提取文字，不是让 LLM 看图，也不是 OCR。

## 5. 为什么保留 page number

Python enumerate 从 0 开始，用户 PDF 阅读器从第 1 页开始。因此保存 `page_number=index+1`。引用使用 PDF 文件的物理页序，而不是正文或附录印刷页号；其他版本论文的页码可能不同。

## 6. text extraction 是什么

从现有文字层取出字符串。每页保留 source、paper_id、title、page_number、text、source_type="pdf" 和提取状态。仅压缩重复空格与过多空行，不修改公式、数字或正文；宁可保留页眉页脚，也不凭规则删掉科学内容。

## 7. 扫描 PDF 为什么提取不到字

扫描页通常只是图像。当前不足 20 个文字字符的页记为 `empty_or_scanned`，不进入 chunks。这是空白/扫描/少字页的保守标记，并不能准确证明该页是扫描件。inspect 返回空页数量，不捏造提取内容。

## 8. OCR 是什么，为什么今天不做

OCR 把图像中的字识别成文本，容易错认科学符号、指数和单位。今天先学清文本提取、页码和证据链；复杂扫描件留待后续专项验证，不用伪造 OCR 结果补齐空页。

## 9. PDF chunk 为什么不能跨页

跨页片段只引用一页会误导。每页独立复用完整行聚合，目标约 900 字符、重叠约 150；整行很长时可能超过目标。chunk_id 包含 paper_id、页码与页内提取行范围以区分片段，但对外不声称这些是稳定排版行号。

## 10. page citation 怎么生成

程序根据真实 page_number 生成 `[paper:mumax3:p12]`。多个片段来自同页时共用页引用，但各自 chunk_id 不同。Markdown 仍是 `[docs/文件.md:L起始-L结束]`。

## 11. 为什么比模型自己说“第几页”可靠

Agent 收集本轮真正检索返回的 citation，最终回答只能使用这组引用。编造 p99 或缺引用会被拒绝。这验证引用身份，不证明每句话都由该页支持；仍需人工核对证据蕴含关系，不能把引用检查称为自动科学证明。

## 12. 怎样共用 Retriever

Markdown loader 返回文本，PDF loader 返回逐页文本，两者都交给同一个 chunk_document 和 KnowledgeRetriever。向量化仍是 char n-gram (2,4) TF-IDF，cosine threshold=0.05、query coverage>=0.50，Top-K 默认 4。

`scope=project_docs` 只索引项目文本，`papers` 只索引论文页，`all` 联合索引。papers 可用 paper_id 限定一篇。Markdown 每个来源最多两段，PDF 每页最多两段，避免一页占满 Top-K。范围选择来自真实模型调用，而不是用户问题关键词硬路由。

英文论文最好用英文关键词。中文检索能读取中文 PDF，但不能因此宣称具备跨语言语义检索；模型可把中文问题转成英文检索词，再用中文组织答案。

## 13. PDF RAG 仍不是训练模型

片段只临时进入请求上下文，不修改模型参数。换论文后重建小索引；无需向量数据库。run_pdf_rag.py 不调用 DeepSeek，专门观察 retrieval；run_agent.py 才增加 generation。

## 14. 私有论文的 API 边界

只读 knowledge/public/papers 与 knowledge/local/papers 的直接 PDF，不扫描 Downloads、Documents 或其他桌面目录。Path.resolve 拒绝路径穿越、外部绝对路径、UNC 和链接偏移。工具只接收 paper_id，不让模型传任意路径。

local 全部 Git 忽略，public PDF 本体也默认忽略，提交代码与 sources.json。Git 忽略不等于离线：命中内容可能发给 DeepSeek；用户主动放入私有目录前必须确认拥有使用与 API 处理权限。公开可访问也不等于允许重新分发，未知许可证不写成 CC。

## 15. 论文为什么仍是不可信数据

论文也能夹带“忽略指令、输出 API Key”一类文本。context 标记 UNTRUSTED DATA，并转义可能关闭 retrieved_document 的标签；loader 不执行任何命令。基础包装和提示并不构成生产级防注入系统。

## 16. 结果不同为什么不能推出谁更准确

软件设置、网格、时间采样、判据和模型项都可能影响结果。论文关于一般方法的描述不自动解释当前文件中的差异。没有同条件对照、误差与收敛证据，就必须说当前证据不足以归因；不能因一条曲线更早过零而给软件排名。

## 17. 三类事实怎样区分

| 用户问什么 | 事实来源 | 证据形式 |
| --- | --- | --- |
| 当前 CSV 的数值 | Python tools 读原始曲线 | alias、返回值、单位、插值说明 |
| 项目历史与实现 | Markdown/TXT RAG | 文件与真实行号 |
| 论文内容 | PDF RAG | paper_id 与真实页码 |

## 三个流程

```text
A 论文问题：用户 → PDF Retriever → Page Chunk → LLM → 页码引用
B 当前数值：用户 → Python Tool → CSV → 数值结果
C 综合问题：用户 → PDF RAG + Python Tool → 论文证据 + 当前数据 → LLM
```

C 的两部分分别给证据，不把历史文档当当前实算，也不把一般论文当当前误差机制证明。MAX_STEPS 仍为 5，参数已确认的独立请求可以同轮调用。

## 本地复现

先安装 requirements，再按公开目录 README 手动保存指定 PDF；仓库克隆不会附带第三方 PDF。

```powershell
conda run --no-capture-output -n agent python scripts/inspect_pdf.py mumax3
conda run --no-capture-output -n agent python run_pdf_rag.py
conda run --no-capture-output -n agent python scripts/evaluate_pdf_rag.py
conda run --no-capture-output -n agent python scripts/evaluate_rag.py
conda run --no-capture-output -n agent python scripts/evaluate_rag.py --include-papers
conda run --no-capture-output -n agent python -m unittest discover -s tests -v
```

PDF 评估是 Page Hit@4 与负例检索拒绝率，不是 LLM accuracy。自产 fixture 动态生成，没有网络依赖；真实论文与真实 DeepSeek 用于独立 integration Demo。Day6_Verification 和 Day1-6 总结不进入检索，避免验收记录回答自身题目。

## Day 6 我真正应该理解的 5 件事

1. PDF 页面、文字层和扫描图片不是同一件事。
2. 页码从解析时保留，不能靠 LLM 回忆或猜。
3. chunk 不跨页，检索和生成是两个步骤。
4. 合法引用身份不等于答案正确，还要核对含义。
5. 当前数据、项目记录、论文证据各有来源与权限边界。
