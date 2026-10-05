# Day 3 本地验收记录

验收日期：2026-10-05。本记录只描述本次实际运行，不保证后续 API 每次选择相同的工具顺序。

## 环境与本地检查

- Conda `agent`：Python 3.12.14。
- 必要依赖：openai 3.22.1、python-dotenv 1.2.4、pandas 3.0.6、matplotlib 3.11.2。
- 运行过 `scripts/generate_synthetic_data.py`，生成 101 行合成数据。
- `python -m unittest discover -s tests -v`：32 项全部通过，含 Day 2 工具回归和 Agent 连续/同轮多工具调用测试。
- `python -m compileall src tests run_agent.py scripts`：通过。
- `git diff --check`：通过。
- 绘图单元测试使用临时目录，结束后清理测试 CSV 和 PNG。

## 六个真实 API Demo

使用 `python run_agent.py`、DeepSeek `deepseek-flash` 和 Responses API，未指定强制工具选择。

| Demo | 实际行为与结果 |
|---|---|
| 1：列出数据集 | 自主调用 `list_datasets`，随后检查唯一合成数据集 |
| 2：查看结构 | 自主调用 `list_datasets`、`inspect_dataset`，确认 101 行、3 列，无缺失值 |
| 3：mumax3_mz crossing | 检查结构后调用 `calculate_switching_time`，得到 73.79872503161886 ps，并用 calculator 验算 |
| 4：比较两列 | 检查结构、分别计算两列 crossing，再调用 calculator；comsol_mz 为 72.59936292317492 ps，更早 1.1993621084439354 ps |
| 5：绘图 | 检查数据后调用 `plot_dataset`，保存 `outputs/plots/mz_vs_time_comparison.png` |
| 6：天为什么是蓝色的 | 直接生成文本，未调用任何工具 |

图像真实存在，大小 44868 字节；目视确认标题标注 SYNTHETIC、两条曲线、横纵坐标、图例和网格完整。

上述时间全部来自合成数据的相邻点线性插值，不能当作真实 MuMax3/COMSOL 科研结果。比较 Demo 完成了一个问题中的连续多工具闭环。

## 开发中发现并修正的解释问题

初测时模型把 `sorted=false` 误读成数据未排序，并对合成曲线作了没有依据的物理机制解释。工具结果增加 `sorting_note`、`data_note`，系统指令要求遵循说明和数据证据。最终复测正确说明输入时间已递增、无需重排，也明确不推断真实软件差异。

PowerShell Conda 激活脚本曾解析失败，误用基础 Python 3.8 的测试结果未用于验收。之后统一通过 `conda run --no-capture-output -n agent` 执行。受限运行中的 matplotlib 字体缓存位置设在 Git 忽略的 `outputs/.matplotlib/`，最终测试未再出现字体缓存权限警告。

## 隐私与 Git

- `.env` 被忽略且未追踪；候选提交文件的当前 API Key 精确匹配扫描、密钥模式扫描均未命中。
- `data/local/` 的内容被忽略，仅保留空 `.gitkeep`。
- `outputs/` 的 PNG 和缓存被忽略，仅保留空 `.gitkeep`。
- 本地真实微磁学 CSV 存在；只检查了是否存在，未读取内容、复制、修改或接入工具。
- 本次只完成本地 Git 提交，按用户要求不执行 GitHub push。
