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

## 实际检查记录（2026-11-03）

四份文件均通过 Notebook 格式验证，并在独立的真实 Python 内核中运行全部单元格。另检查了交互按钮的单步、运行到结束、重新初始化、非法输入保留原状态，以及同优先数进程按 P1 至 P5 运行两轮的 10 步结果，均通过。

| 文件 | 本次运行总步数 | 结果 |
| --- | ---: | --- |
| exp4-complete.ipynb | 14 | 通过 |
| 实验4_动态优先数进程调度 - 副本.ipynb | 14 | 通过 |
| 实验4_动态优先数进程调度.ipynb | 35 | 通过 |
| 实验4_动态优先数进程调度_未执行.ipynb | 50 | 通过 |

随机版本的步数随初始参数变化；检查要求总步数等于五个初始运行时间之和，最后所有进程为 E、剩余时间和 next 均为 0，队首为 0。验证在内存和本地检查副本上完成，未将未执行版改成已执行版。

隐私复查覆盖四份文件的正文、源码、输出及元数据：未发现已知私人身份、个人邮箱、个人用户目录路径、手机号、身份证号或常见密钥模式。文件内无附件或嵌入图片，元数据未包含作者身份。检查脚本、执行副本和日志仅保存在被忽略的 `.privacy-review/` 中。
