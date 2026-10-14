# 实验 2 的四个 PiCreature

这一步只准备角色与预览，不包含进程同步、水果或实验演示逻辑。

| 类 | 造型 | 构造高度 | 身体颜色 |
| --- | --- | --- | --- |
| `FatherPi` | 原版 Randolph 成人比例 | 3.0 | 深蓝 `#176477` |
| `MotherPi` | 成人比例，爸爸的 90%，仅加睫毛 | 2.7 | 深红 `#B83F49` |
| `SonPi` | 原版 BabyPiCreature | 1.5 | 天蓝 `#77C9EF` |
| `DaughterPi` | 相同 Baby 比例，仅加睫毛 | 1.5 | 浅红 `#F27983` |

构造高度是传给原作者构造器的数值。Baby 随后把眼睛放大 1.2 倍，瞳孔再放大 1.3 倍，
所以最终整体边界高度可能稍大于 1.5。儿子与女儿的身体、眼睛和瞳孔尺寸相同；
睫毛不参与身体缩放。没有蝴蝶结、头发、衣服或其他饰物。

## 运行

使用现有 `manim` conda 环境。已在 Python 3.12.15、ManimGL 1.7.2 的本地源码安装中验证。
依赖记录见 `requirements.txt`。以下命令从仓库根目录开始：

```powershell
conda activate manim
cd exp2/src
python -m pi_family.render_previews
```

在 `pi_family/preview/` 生成四人合照 `family.png` 和视线、眨眼预览 `family_motion.gif`。
预览使用 ManimGL 实际渲染，不需要 FFmpeg；生成文件被 Git 忽略。

使用 ManimGL 窗口观看：

```powershell
manimgl pi_family/preview_scene.py FamilyPortrait
manimgl pi_family/preview_scene.py FamilyMotion
```

## 后续场景复用

场景位于 `exp2/src` 时可以直接导入：

```python
from manimlib import LEFT, RIGHT, Scene
from pi_family import Blink, FatherPi, MotherPi, SonPi, DaughterPi

class Example(Scene):
    def construct(self):
        father = FatherPi()
        mother = MotherPi().shift(3 * RIGHT)
        son = SonPi().shift(3 * LEFT)
        daughter = DaughterPi().shift(5 * RIGHT)
        self.add(father, mother, son, daughter)
        self.play(mother.animate.look(LEFT))
        self.play(Blink(mother), Blink(daughter))
        self.play(son.animate.shift(RIGHT))
```

睫毛属于角色自身，整体移动、缩放、翻转、淡入淡出时会一起变化。
眨眼沿用原作者的 `Blink`；女性角色的 `blink()` 同时闭合睫毛，动画结束后一起恢复。
眼睛仍保留作者的 iris/pupil 两部件结构，视线计算使用原有眼睛边界。
包含正常的 `plain` 姿势，以及基于它自行生成的左手伸出、放置两个姿势。
其他表情须先取得对应 SVG。
完整来源、改动与授权见 `SOURCES.md`。

## 左手放置动作

这里只改变原图左边向下弯的凸起，右侧、双腿和面部保持固定。
完整动作约 2 秒：略抬起并伸出、轻轻放下、停顿、收回。
四个角色使用同一动作比例，整体 `flip()` 后会在镜像方向执行。
本预览没有视线变化或眨眼，也不加入桌子和物品。

```powershell
manimgl pi_family/preview_scene.py LeftHandPlacementDemo
python -m pi_family.render_hand_preview
```

第二条命令在 `pi_family/preview/` 生成 `left_hand_placement.gif`、
`hand_start.png` 和 `hand_place.png`，不需要 FFmpeg。

场景中可以复用完整动作：

```python
from pi_family import FatherPi, place_left_hand

pi = FatherPi()
self.add(pi)
place_left_hand(self, pi, run_time=2.0)
```

也可把角色组传给 `place_left_hand(self, family)`，同时播放。
内部依次调用原作者风格的 `self.play(pi.change(mode), rate_func=smooth)`。
角色采用固定曲线对应关系，逐帧保留未变形顶点；目标 SVG 只改左手路径，
原来的右侧、双腿以及眼睛和嘴巴的 SVG 指令保持原样。

两份目标 SVG 已随项目保存；需要重新生成时运行：

```powershell
python pi_family/hand_poses.py
python -m pi_family.verify_hand_motion
```

## 已执行的验证

- 爸爸的身体点数据与原版成人一致，妈妈的身体点数据为其 0.9 倍。
- 两个孩子的身体、眼睛和瞳孔点数据与原版 Baby 构造结果一致。
- 四个角色实际执行 `Blink`，闭合后恢复原点数据；女性睫毛一起闭合和恢复。
- 睫毛随整体移动、缩放和翻转，眼睛仍为 iris/pupil 两部件。
- 已实际渲染 1280×720 合照与 107 帧动画，并人工检查静态画面。
- 左手动作已检查四个角色及其镜像、缩放和移动后的版本。
  每段过渡采样 21 个时刻，非手臂身体顶点、肩部连接点、眼睛、嘴巴和睫毛
  的点数据逐项保持完全相等；动作结束恢复普通姿势。
- 已检查目标 SVG 的五个其他部件，以及身体路径中手臂之外的前后段保持原样。
- 已实际渲染左手动作的 95 帧，并逐像素比较：四个左手区域之外的画面完全不变。
  GIF 使用同一调色板，保持静止区域的颜色一致。
