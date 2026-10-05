# GitHub 展示设置建议

以下设置由用户在 GitHub 网页手动完成，本项目没有自动修改远程仓库。

## Repository Description

`Physics Research Agent for scientific data analysis, tool calling and grounded RAG.`

## Topics

`ai-agent`、`rag`、`llm`、`physics`、`scientific-computing`、`python`、`deepseek`、`micromagnetics`、`tool-calling`

## 展示建议

1. 仓库可见性改为 Public 前，先再次确认 Git history 中没有密钥、真实科研数据或第三方 PDF 本体。
2. 在 About 中设置 Description 与 Topics；Website 留空，除非以后确有公开部署。
3. README 首屏保留一句话定位、三张截图和 Quick Start。
4. Pin 到个人主页时，配合一行说明：“AI-assisted learning project with honest evaluation and public/private data boundaries.”
5. Release、Pages、Actions 均不是 Day 7 必需项，不为“看起来完整”而虚构部署。

## Public 前人工核对

- [ ] `.env` 与 API Key 不在 tracked files 或历史中
- [ ] `config/data_sources.local.json` 未提交
- [ ] `data/local`、`outputs`、`knowledge/local` 无私人内容
- [ ] `knowledge/public/papers/*.pdf` 未提交
- [ ] 三张截图只含公开 safe demo
- [ ] README 中真实科研数值带授权/不公开/不代表精度的边界说明
- [ ] GitHub 仓库描述没有“生产级”“99% 准确率”等不实表述
