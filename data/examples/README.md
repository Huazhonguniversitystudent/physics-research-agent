# SYNTHETIC / 合成微磁学示例数据

`synthetic_micromagnetics.csv` 仅用于演示 Agent 的工具调用、CSV 检查、翻转时间插值和绘图，不是真实实验或模拟原始数据。

- 生成脚本：`scripts/generate_synthetic_data.py`。
- 时间列：`time_ps`，0–100 ps，间隔 1 ps，101 个数据点。
- 演示磁化列：`mumax3_mz`、`comsol_mz`，无量纲。
- 公式：`mz = tanh((time_ps - t_switch) / 5)`。
- 设定零点：分别为 73.8 ps、72.6 ps；CSV 值保留 10 位小数。
- 这两个列名不代表实际运行过 MuMax3 或 COMSOL，参数不是科研结论。

线性插值从采样后的相邻点估计 crossing，因此工具结果会略微偏离连续函数设定的零点。数据来源、数值截断和插值方法应与结果一起说明。

公开目录仅放可以分享的数据。真实私有数据未来由用户自行选择放入 `data/local/`，工具会把其元数据标为 `source=local`、`synthetic=false`；这个标记不验证数据的真实性。`examples` 中名称以 `synthetic_` 开头的文件按约定标为合成数据。
