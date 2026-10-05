# Day 6 验收记录：公开论文 PDF RAG

验收日期：2026-10-05。本记录基于本地实际执行，不把 fixture 当成公开论文，不把 mock 当成真实 API，也不把检索命中率称为回答准确率。本文与 Day1-6 总结不参与索引。

## 环境与范围

- PowerShell 普通 activate 的 Python 仍指向 base 3.8.13；全程开发与验收使用 `conda run --no-capture-output -n agent python ...`。
- 实际 Python：3.12.14；PyMuPDF：1.28.2。
- openai 3.22.1、python-dotenv 1.2.4、pandas 3.0.6、matplotlib 3.11.2、scikit-learn 1.9.1。
- DeepSeek：deepseek-flash，Responses API，MAX_STEPS=5，14 个注册工具（Day 5 的 12 个，加论文 list/inspect）。
- 仅新增 PyMuPDF，不安装 OCR、pdfplumber、pypdf 或 reportlab；没有多 Agent、embedding、数据库、Web UI、自动下载器。
- 真实科研源仅由原有 alias 工具只读，未修改原始 CSV、注册表或科研算法。

## 公开论文与解析

标题：The design and verification of Mumax3。

作者：Arne Vansteenkiste、Jonathan Leliaert、Mykola Dvornik、Felipe Garcia-Sanchez、Bartel Van Waeyenberge。年份：2014。注意这是 arXiv v3 的五位作者，不混用含 Mathias Helsen 的期刊版名单。

来源：[arXiv:1406.7635v3](https://arxiv.org/abs/1406.7635v3)，PDF：https://arxiv.org/pdf/1406.7635v3 。最终经最新入口 https://arxiv.org/pdf/1406.7635 下载；本地第一页明确标记 `arXiv:1406.7635v3 10 Jul 2014`，与固定版本一致。没有使用来源不明的镜像或私人文件。

访问记录：`publicly accessible source; license not verified`。没有将软件 GPLv3 误认为论文许可。PDF 本体不重新分发，sources.json 可提交。

| 项目 | 实测值 |
| --- | ---: |
| paper_id | mumax3 |
| 本地相对文件 | knowledge/public/papers/mumax3_design_v3.pdf |
| 完整文件大小 | 2,081,564 bytes |
| PDF 物理页数 | 32 |
| 可提取页数 | 32 |
| empty_or_scanned | 0 |
| 轻量清洗后文字字符数 | 64,767 |
| PDF chunks | 104 |
| Markdown/TXT documents / chunks | 11 / 139 |
| 联合索引 documents / chunks | 43 / 243 |

联合 documents 是 11 份文本 + 32 个 PDF 页面，不是 43 篇论文；底层只有 1 篇论文，共 12 个来源文件。空页不会成为 chunk。

SHA256：`82b9669c033275e0856e9f02d8bf19976db19e95cadedd24d57337fdd344f9a3`。

用 PyMuPDF 渲染并查看 p2/p12，核对单元位置和时间积分正文；提取文本已实际读 p2、p3、p4、p12、p13、p15、p16。图中数值和公式会拆成行，不声称布局/公式完全解析。p12 有 RK32 与 RK23 写法不一致，原样保留，未按经验改写科学文本。

## 引用、检索与安全

PDF 引用 `[paper:mumax3:p12]`：1-based PDF 页序。多个页内 chunks 可共享 citation，但 chunk_id 唯一；不伪造稳定 PDF 行号。Markdown 保持 `[source:Lstart-Lend]`。最终校验只允许本轮实际返回过的引用；缺引用、fake:p99 均拒绝。

统一 KnowledgeRetriever，char n-gram (2,4)、cosine threshold=0.05、coverage>=0.50、默认 Top-K=4。Markdown 每来源最多 2 段，PDF 每页最多 2 段。scope=project_docs/papers/all，paper_id 仅用于 papers。没有另写 PDF 专用算法。

只读允许目录直接存放的 PDF，用 Path.resolve 检查最终路径。拒绝 ..、外部绝对路径、UNC 与链接偏移；模型工具接收 paper_id，而不是文件路径。列表与 inspect 只回相对来源、元数据和短摘要，不回全文或本机绝对地址。

PDF 是 UNTRUSTED DATA，context 转义标签，不执行文本指令；这只是基础防护。私有文件不进 Git，但命中片段可能发送 DeepSeek，放置前必须确认授权。

## PDF Retrieval Evaluation

实际执行 `scripts/evaluate_pdf_rag.py`。6 个正例来自上述实际页面，2 个负例保留，没有为了凑 100% 删题。page_hit_at_4=6/6=100%；negative_rejection=1/2=50%。脚本诚实退出 1，表示固定评估集仍有失败，不能写成“全部通过”。

| 问题主题 | 可接受页 | 实际 Top-4 页序 | 结果 |
| --- | --- | --- | --- |
| FD / orthorhombic cells | 2 | 2,2,5,1 | 命中 |
| OVF input/output | 3 | 3,2,19,1 | 命中 |
| magnetostatic FFT convolution | 4 | 4,5,18,5 | 命中 |
| RK45 / Dormand-Prince 默认动力学 | 12 | 12,12,20,20 | 命中 |
| Relax 内部 RK23 | 13 | 13,13,15,21 | 命中 |
| standard problem 4 / zero crossing | 15,16 | 15,15,14,14 | 命中 |
| 英文 Mozart / Magic Flute 剧情 | 无 | 13,12,17,18 | 误召回，失败 |
| 中文 GPT-6 / 量子霍尔标准 | 无 | 空 | 检索拒绝，通过 |

英文歌剧负例 top_score=0.166883、coverage=0.802721。通用英文 n-gram 在长英文论文里高度重叠，因此现有阈值不能可靠识别未知主题。没有为该负例单独上调阈值或硬编码拒绝词。

另做中文直检诊断：“根据论文，MuMax3使用什么数值方法，请给出处”：found=false、coverage=0.222222、top_score=0.134447。英文论文不等于自动跨语言语义检索；Agent 实际将问题转为英文关键词。评估题用于开发，含提示性关键词，不是独立 holdout。

## Day 5 Markdown 回归

| 阶段 / 范围 | documents / chunks | 正例 Hit@4 | 负例拒绝 |
| --- | --- | --- | --- |
| Day 6 修改前 Day 5 baseline | 9 / 112 | 8/8 | 4/4 |
| 新学习文档加入的中间状态 | 11 / 136 | 8/8 | 4/4 |
| 最终文本库 / project_docs | 11 / 139 | 8/8 | 4/4 |
| 最终联合库 / all | 43 / 243 | 7/8 | 4/4 |

两种命令均实际执行：`scripts/evaluate_rag.py` 和 `scripts/evaluate_rag.py --include-papers`。联合模式脚本退出 1，不隐瞒这一退化：“Day 4 真实 MuMax3 和 COMSOL switching time 是多少？”没有把指定的 Day4_Real_Data_Validation 放进 Top-4，被论文、README 与其他记录挤占。switching time 定义题也新增了 PDF 命中，排名不再相同。

采用已实现的 scope 隔离：项目事实 instructions 明确 project_docs，论文事实 papers；最终 project_docs 保留全部 12 题通过，不更换 TF-IDF 或修改旧题 expected_sources。不能声称 all 的排序完全无退化。

## 真实 run_agent.py Demo

全部实际向 DeepSeek 发起请求，不使用 mock 来替代真实 Demo。每个问题新建 conversation，工具名和参数为实际模型选择；部分请求使用 top_k=5/6，单独固定评估仍用 top_k=4。

| Demo | 实际问题 / 工具链 | 实际结果 |
| --- | --- | --- |
| 1 | 目前知识库里有哪些论文？→ list_knowledge_papers | 1 篇 mumax3，本地可读，作者/年份正确 |
| 2 | 检查 mumax3 的基本信息与页数 → list + inspect_paper | 32 页，32 页可提取，0 空页，64,767 字符 |
| 3 | 空间离散方法、物理量位置 → search papers（英文关键词）+ list | FD，2D/3D orthorhombic cells；体量在中心、界面量在面；引用 p2，另有 p1 |
| 4 | 默认 Runge-Kutta 方法 → list + search papers | RK45 Dormand–Prince；引用 p12 |
| 5 | GPT-6 训练参数与量子霍尔电阻标准 → list + 三次 papers search | 首轮拒绝编数值但断言“全文没有”，未通过证据措辞标准；加强提示后真实重测，明确当前片段证据不足，不可断言全文不存在；引用 p2/p14/p15 等说明误召回实际主题 |
| 6 | 项目文档 Tool Calling 谁执行 Python？→ search project_docs | 本地 Python 执行，模型只请求；引用 Day2 L44-L70，没有 PDF 干扰 |
| 7 | 当前 fem_fdm_j25 switching time → list_external + inspect_external + compare | MuMax3 73.83834774284676 ps，COMSOL 72.81911124409665 ps，差 1.019236498750118 ps；回答可四舍五入，没有 RAG |
| 8 | 12345 * 6789 → calculator | 83810205（工具浮点表示 83810205.0） |
| 9 | 天为什么是蓝色？→ 直接 LLM | 瑞利散射解释，没有工具调用；仅验证普通问答路由，不把所有补充科普逐句视为已科学审核 |

Demo 5 的最终回答没有编出训练参数或电阻数值，保留了 Top-K 不等于全文审读的限制。额外歌剧 Agent 诊断也拒绝把剧情包装为论文内容，但第一句仍出现“论文里没有”的过强措辞，后文才补充 Top-K 限制；这项额外测试是尚存的生成措辞风险，不写成完全解决。

## 综合 Demo

实际输入：“根据公开 mumax3 论文说明默认动力学时间积分方法，再告诉我当前 fem_fdm_j25 的 switching time，单位 ps。两部分分别给页码出处和当前数据来源。”

实际工具链：list_knowledge_papers、list_external_datasets、list_datasets → search papers + inspect_external_dataset → 两次 summarize（MuMax3/COMSOL）与 compare_switching_times → 最终回答。总计 8 次工具执行，部分在同一轮请求，Python 逐个执行，未触发 5 轮限制，未把 MAX_STEPS 改为 6 或更大。

回答给出默认 RK45，引用 `[paper:mumax3:p12]`；独立报告 alias fem_fdm_j25 和两份粗网格原始曲线、相邻点插值方法及上述两个 ps 数值。没有把论文当成当前 CSV 实算，也明确当前片段不足以给约 1 ps 差异归因。

## 测试与检查

实际执行 `python -m unittest discover -s tests -v`：**105/105 通过**。原 Day 2–5 的 79 项保留；新增 PDF 22 项、Agent PDF/参数回传 4 项。全部测试无需 DeepSeek、公开论文下载或真实科研目录；fixture 由 PyMuPDF 动态在临时允许目录生成，四页自写中英文、注入文本、空页。没有第三方 fixture 内容。

覆盖：public/local 路径、穿越、外部绝对路径、UNC、链接逃逸、损坏 PDF、1-based、提取/空页、跨页禁止、重叠、unique chunk_id、中英检索、引用身份、fake p99、注入转义、Git ignore、排除 env/registry/CSV、scope、非法 JSON 参数。后端参数校验不依赖模型正确。

- `python -m compileall src tests scripts run_agent.py run_rag.py run_pdf_rag.py` 通过。
- `git diff --check` 通过（Windows LF/CRLF 提示不是错误）。
- inspect_pdf 和 run_pdf_rag 真实运行；后者 FFT 检索第一名 p4、score=0.3176，无 DeepSeek 调用。
- `.env`、local registry、data/local、outputs、knowledge/local/papers、public PDF 均 check-ignore 通过，大小写 PDF 扩展名均覆盖。
- 私有目录只允许 tracked .gitkeep；不提交真实 CSV/PNG、密钥、私人 PDF 或第三方 PDF 本体。

## 开发问题与诚实边界

1. 先写测试时 loader 尚不存在，测试 ImportError；实现后通过，非伪造“始终通过”。
2. PowerShell/curl 沙箱 TLS 凭据限制、HTTP 406、慢下载超时均真实出现。一度得到不完整文件，PyMuPDF 只能修复成 0 页，未用于 Demo。最终正常 TLS 下载到临时文件，验证 32 页且 is_repaired=false 后替换；没有关闭证书校验。当前 loader 显式拒绝 0 页文档。
3. 全英文未知主题误召回、中文直检不足、all 排名退化均保留记录；没有删除失败题追求 100%。
4. 模型初次把证据不足改成全文否定，已加强提示并重测，但额外负例显示生成边界仍有风险。citation identity 不验证 claim entailment。
5. 双栏、公式、图表与页眉解析有限，无 OCR、embedding、holdout 或生产级防注入。所有论文方法说明仅对应这份 2014 v3，不当成当前软件版本文档。

## Git 交付

保留原有历史，在 main 上创建功能与总结两次本地 commit；最终 hash 与 ahead 数在终端复核后汇报。未执行 push、同步、reset、rebase 或 force push。用户手动 push。
