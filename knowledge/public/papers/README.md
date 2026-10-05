# 公开论文目录

这里只放明确公开可访问、可用于学习检索的文本型 PDF。第三方 PDF 本体默认 Git 忽略，不重新分发；提交来源记录 `sources.json`。

本地演示使用 arXiv:1406.7635v3《The design and verification of Mumax3》，2014 年，下载地址：https://arxiv.org/pdf/1406.7635v3 。手动保存为 `mumax3_design_v3.pdf`。没有自动论文下载器，克隆仓库后需要自行下载这一份文件。

`sources.json` 是数组，每项记录 paper_id、title、authors、year、source_url、license_or_access_note、local_filename。paper_id 仅字母、数字、下划线、连字符；local_filename 必须是本目录内的 PDF 文件名。未登记的 PDF 使用文件名 stem 作为 paper_id，作者与年份为未知。

不要把软件 GPLv3 许可误当成论文许可。此 PDF 仅确认公开可访问，记录为 `publicly accessible source; license not verified`。

私有论文只放 `knowledge/local/papers/`，必要时在该目录添加相同格式的 sources.json，全部忽略。Git 忽略不意味着 API 离线：命中片段可能发送给 DeepSeek，必须先确认授权。当前不支持 OCR，也不扫描整机。
