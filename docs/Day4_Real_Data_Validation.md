# Day 4：真实数据验证记录

验证日期：2026-10-05。范围：现有固定电流粗网格结果的只读复现，不重新运行模拟、不调整模型参数、不把数值分析称作软件精度结论。

## 数据源与实际结构

本地注册 5 个 alias；绝对路径仅保存在被忽略的 `config/data_sources.local.json`。

| Alias | 文件名或组成 | 用途 |
| --- | --- | --- |
| fem_fdm_j25 | 下方两条原始曲线组合 | 比较、采样、绘图 |
| mumax3_j25_coarse | MuMax3_粗网格_J2.5E12_体积平均.csv | MuMax3 原始曲线 |
| comsol_j25_coarse | COMSOL_粗网格_J2.5E12_体积平均.csv | COMSOL 原始曲线 |
| fem_fdm_j25_summary | FEM_FDM_J2.5E12对比.csv | 3 行既有汇总，校验用途 |
| fem_fdm_jc_summary | FEM_FDM_Jc对比.csv | 3 行临界电流汇总，只 inspect |

两份原始曲线各 101 行，识别到 `time_ps`、`avg_mz`，时间单位 ps。MuMax3 为 UTF-8 BOM，COMSOL 为 UTF-8，分隔符都是逗号。组合为 202 行的长表 `time/mz/source`，两列为 float64，来源列为字符串，选定列无缺失值。

**行数相同不等于时间网格相同**：MuMax3 存在非整数原生时间点，COMSOL 为整数 ps 采样。适配器保留各自时间，不先对齐、不预先重采样。

发现的 `FEM_FDM_J2.5E12对比.csv` 本身是汇总表，不是 `time_ps,mumax3_mz,comsol_mz` 时间序列；所以追溯其来源，注册原始曲线复算，而不是拿汇总结果假装重新算了一遍。其 `*_source` 字段的私有路径在 inspect 预览中隐藏。Jc 汇总并未用于本次 switching time 算法。

## 方法与结果

判据：首个相邻区间满足 `m1 < 0 <= m2`。共用 Day 3 提取的 crossing 算法，在区间内线性插值：

```text
t_switch = t1 + (0 - m1) * (t2 - t1) / (m2 - m1)
```

| 来源 | switching time / ps | mz(100 ps) |
| --- | ---: | ---: |
| MuMax3 | 73.83834774284676 | 0.9564934 |
| COMSOL | 72.81911124409665 | 0.962276697685 |

COMSOL 的首次负到正过零更早，绝对时间差为 **1.019236498750118 ps**。输入时间本身已递增，`sorted=false` 表示未重新排序；不表示输出顺序混乱。

过零区间：MuMax3 为 73.07048664640516–74.00312770383329 ps；COMSOL 为 72–73 ps。这是线性插值得到的时间估计，不意味着模拟本身具备这些小数位的物理精度，也不等于磁化已达到 +1。

100 ps 查询采用 `linear` 模式，但两条曲线均存在精确的 100 ps 采样点，因此返回原始点，`interpolated=false`，不发生插值或外推。

与历史参考 73.84/72.82 ps、0.95649/0.96228 在其保留位数上完全一致。再将当前原始曲线复算值与当前 J2.5E12 汇总表粗网格行核对：两个过零时间与两个 100 ps 值的绝对误差均为 0.0（当前读入的浮点表示下）。没有为了匹配参考改变算法。

## 图与真实 API 验收

实际生成并查看：`outputs/plots/fem_fdm_j25_mz_comparison.png`。包含时间/磁化坐标、MuMax3/COMSOL 图例、标题、网格和 tight layout，直接绘制原生点。PNG 只留本地，不放公开文档、不提交 Git。

八项通过 `run_agent.py` 实际请求 DeepSeek 的 CLI 验证，不是只 mock 模型：

| Demo | 实际行为 | 结果 |
| --- | --- | --- |
| 1 列出真实数据 | list_external_datasets | 5 个注册 alias，均存在，无绝对路径 |
| 2 检查 fem_fdm_j25 | inspect_external_dataset | 202 行；组件各 101 行；单位 ps |
| 3 比较过零时间 | inspect → compare_switching_times | 上述真实时间与差值 |
| 4 查询 100 ps | inspect → 两次 sample_value_at_time | 上述两数，精确采样点 |
| 5 真实绘图 | inspect → plot_dataset | PNG 实际存在且已视觉检查 |
| 6 合成数据比较 | Day 3 inspect/calculate；calculator 求差 | 73.79872503161886、72.59936292317492、差 1.1993621084439354 ps |
| 7 乘法 | calculator | 83810205 |
| 8 蓝天原因 | 模型直接解释瑞利散射 | 没有调用工具 |

如实记录：首轮 Demo 6 曾将仓库文件名传给外部 alias 工具，被校验拒绝后恢复。已收紧 instructions 和 schema，并单独复测同一问题：正确选 Day 3 工具，完成比较和合成绘图。初次 Demo 2 的自然语言还曾误说采样点数不同，而元数据明确各 101 行；已补充“同样行数不等于同样时间点”的约束。工具数值可复现，但自然语言解释仍需要审阅，不保证任意后续请求永不选错工具。

## 回归、只读与提交隔离

最终本地 `unittest`：**61 项全部通过**，包含 Day 2/3 回归；`compileall`、`git diff --check` 通过。新增测试只用小型 synthetic fixture 和临时注册表，不依赖用户目录或联网。

四份本次实际使用的真实 CSV 在分析前后 SHA-256 一致，未修改原始文件；无真实数据批量复制。源只读，输出只写项目的 ignored 目录。

提交前核对 `.env`、`data/local/`、`config/data_sources.local.json`、`outputs/` 的 Git 忽略规则；公开修改只含代码、模板、synthetic fixture、中文文档。本地配置、API Key、真实 CSV、真实 PNG 均不提交。工具回传是摘要/少量预览及派生数值，不是全部原始 CSV；这些必要摘要会通过 API 发送给 DeepSeek，不应把 Git 隔离理解为离线处理。

本次只做本地 commit，不执行 push。后续核查命令：`git status -sb`、`git log --oneline -5`、`git check-ignore config/data_sources.local.json`。
