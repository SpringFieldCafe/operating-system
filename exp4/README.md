# 实验 4：动态优先数进程调度

四份 Notebook 均为正式版本，保留各自的文件名与内容。

| 文件 | 初始参数 | 保存的结果 |
| --- | --- | --- |
| [实验4_动态优先数进程调度.ipynb](src/实验4_动态优先数进程调度.ipynb) | 五组随机参数，优先数和运行时间均为 1–15 | 已保存运行输出 |
| [实验4_动态优先数进程调度_未执行.ipynb](src/实验4_动态优先数进程调度_未执行.ipynb) | 五组随机参数，优先数和运行时间均为 1–15 | 保留未执行状态，无运行输出 |
| [exp4-complete.ipynb](src/exp4-complete.ipynb) | 固定参数，总运行时间 14 | 已保存运行输出，含上机步骤和结果分析 |
| [实验4_动态优先数进程调度 - 副本.ipynb](<src/实验4_动态优先数进程调度 - 副本.ipynb>) | 固定参数，总运行时间 14 | 已保存运行输出，含上机步骤和结果分析 |

## 运行方法

在仓库根目录执行，依赖版本见 [requirements.txt](requirements.txt)：

```powershell
python -m pip install --timeout 60 -r exp4/requirements.txt
python -m jupyter lab
```

打开任意一份 Notebook，选择 Python 3 内核，从上到下运行全部单元格。在交互区修改参数后点击“初始化”，再使用“单步调度”或“运行到结束”。优先数须为整数，运行时间须为正整数。随机版重新运行第 5 节可生成新参数，再运行第 6、8 节更新静态结果与交互区。

GitHub 上的静态预览不能运行交互按钮。未执行版需在 Jupyter 中运行后才能看到结果。

## 验证方法

以下命令会在真实内核中逐份执行，并触发 Notebook 自带的断言。执行副本写入本地检查目录，四份正式文件保持原样。

```powershell
New-Item -ItemType Directory -Force .privacy-review/exp4-recheck | Out-Null
Get-ChildItem -LiteralPath exp4/src -Filter *.ipynb | ForEach-Object {
    python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=90 --output-dir=.privacy-review/exp4-recheck $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "Notebook execution failed" }
}
```
