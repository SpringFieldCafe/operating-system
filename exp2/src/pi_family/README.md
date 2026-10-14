# 实验 2 的四个 PiCreature

这里准备角色、动作、空心水果、二维桌盘及预览，不包含进程同步或实验演示逻辑。

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
表情与欢呼通过下方的 `FamilyBehavior` 接口调用。
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

## 持续眨眼与独立扫视

```powershell
manimgl pi_family/preview_scene.py FamilyIdleDemo
python -m pi_family.render_idle_preview
python -m pi_family.verify_idle_motion
```

`FamilyIdleDemo` 从开始到结束持续运行眼睛小动作，先等待 4 秒，
再播放保留的 2 秒放置动作，随后再等待 7 秒。窗口进入交互观看后计时仍继续。
`LeftHandPlacementDemo` 仍保留原来仅动左手的演示。
第二条命令以固定种子 42 导出 `pi_family/preview/family_idle.gif`，便于报告复现。

- 每个角色独立随机每 3–5 秒开始一次眨眼，单次 0.25 秒。
  所有角色采用同样的闭合与恢复曲线，女性睫毛一起眨眼。
- 爸爸、妈妈、儿子和女儿各有 3 套不同的短扫视，总共 12 套。
  每套包含两次短暂观察并回到中间，视线间停留 0.7–1.3 秒，
  两套扫视间休息 3–5.5 秒。孩子的瞳孔观察幅度略大。
- 三套扫视分别打乱顺序播放，每轮都会用到全部版本。
  四个角色各自使用独立随机流，眨眼随机流也与扫视随机流分开。
- 眼睛动画在场景时钟上持续更新，放置动作不会停止或重新计时。
  原有手部动作函数及两份手部 SVG 保持不变。

复用时，先把角色加入场景，然后开启小动作：

```python
from pi_family import enable_idle, make_family, place_left_hand

family = make_family()
self.add(family)
idle = enable_idle(self, family)        # 每次播放都随机
# idle = enable_idle(self, family, seed=42)  # 报告录制时可复现
self.wait(4)
place_left_hand(self, family)
self.wait(8)
# idle.stop()  # 需要结束小动作时调用，会恢复睁眼状态
```

也可以传入单个角色。整体镜像、移动或缩放后，眼睛和睫毛会继续跟随。
小动作开启期间由计时器控制脸部；需要手动控制视线或眨眼时，先 `idle.stop()`。
时间范围通过 `IdleSettings` 配置，扫视方向在 `idle_motion.py` 的 `GAZE_VERSIONS` 中。

验证包含每个角色 60 秒的计时、固定种子的逐帧与跳时复现、
所有扫视版本覆盖、镜像眨眼、手部动作在闭眼时的轨迹兼容，以及计时不中断。
额外运行原来的 `verify_hand_motion`，确认仅手部演示保持原行为。
已实际渲染约 13 秒、392 帧的预览，检查了不同角色的眨眼、扫视及与放置动作同播；
ManimGL 场景命令也已执行验证。

## 表情、等待与取回后的庆祝

本节预览展示角色行为与状态接口。尚未加入水果、桌子、盘子容量、
进程或信号量；预览中的状态是动作示意，不能当作实验程序的执行顺序。

| 角色与状态 | 行为 |
| --- | --- |
| 父母可操作 | 每轮独立抽一次：正常、浅笑各 50%；这一轮保持稳定 |
| 四人阻塞等待 | 平滑变成轻微撇嘴，只改变嘴巴 |
| 儿子成功取回橘子 | 收回手以后，开心、欢呼各 50% |
| 女儿成功取回苹果 | 收回手以后，开心、欢呼各 50% |
| 孩子庆祝结束 | 恢复正常嘴形与手部姿势，从当前眼神接回随机扫视 |

“等待”表示同步条件尚未满足：例如父母没有可用盘子位置，
或孩子尚未取得自己需要的水果。普通停顿、动画的 `Scene.wait()` 不会自动变成等待表情。
`ready()` 和 `waiting()` 都允许重复通知同一状态；重复通知不会重新抽表情或重启嘴形过渡。
父母通过 `parent_placed()` 开始下一轮并重新抽取，或显式调用 `ready(pi, new_round=True)`。

孩子的开心使用公开收藏副本中的笑嘴；欢呼使用其张嘴笑与两侧手端上扬轮廓。
身体曲线保持相同顶点对应关系，腿部点数据保留。颜色、Baby 眼睛比例及女性睫毛沿用现有角色。
父母浅笑及四人的等待嘴形由本项目绘制，只替换正常 SVG 的最后一条嘴部路径。

眨眼仍使用原作者的 `PiCreature.blink()` 和 `Blink`，视线目标仍由原作者的 `look()` 计算。
孩子庆祝时从当前瞳孔位置，用 0.35 秒平滑转向手中位置；其他角色继续随机扫视。
视线可以跟随移动的水果对象或目标函数。默认目标是现有左手上的一个定位点，预览不画水果。
庆祝进入、停留、退出分别为 0.45、0.9、0.45 秒；嘴形过渡为 0.3 秒。
这些时长可用 `ReactionSettings` 调整，完全不决定未来同步程序的执行顺序。

眼睛与嘴形定位使用三个位于角色内部的透明点，随整体移动、缩放、镜像，
不会根据变化中的嘴巴宽度、闭眼高度重新缩放角色。
同一场景时钟先合成身体和嘴，再合成视线和眨眼；眨眼计时始终持续，不因庆祝重置。
退出关注时丢弃暂停的旧扫视目标，从当前瞳孔开始下一段，不补播积压的扫视。

从仓库根目录运行：

```powershell
conda activate manim
cd exp2/src
python pi_family/expression_assets.py
manimgl pi_family/preview_scene.py FamilyExpressionDemo
```

下载命令只读取两个固定版本的公开参考 SVG，核验 SHA-256 后保存到
`pi_family/assets/reference/`。原始参考文件仅保存在本地缓存，不随本仓库提交；
运行预览前需下载一次。来源与角色设计许可说明见 `SOURCES.md`。
无需更换当前 ManimGL 环境。

导出及验证：

```powershell
python -m pi_family.render_expression_preview
python -m pi_family.verify_reactions
```

导出 `pi_family/preview/family_expressions.gif`，约 24.5 秒，736 帧，固定种子 12。
这个种子展示父母的两种可操作表情，以及两个孩子各自的开心和欢呼；
普通窗口预览默认不固定种子。女儿在这个预览里镜像显示，用于展示对称动作。

状态接口示例：

```python
from pi_family import enable_behavior, make_family, take_left_hand

family = make_family()
self.add(family)
behavior = enable_behavior(self, family)
father, mother, son, daughter = family

behavior.waiting(son)     # 由同步程序通知：暂时没有橘子
behavior.ready(son)       # 由同步程序通知：已经可以取橘子
take_left_hand(self, son)
behavior.child_received(son, "orange")  # 默认独立随机 50/50
# 有水果图形时：behavior.child_received(son, "orange", look_target=fruit)
self.wait(behavior.reaction_settings.celebration_duration)
```

`enable_behavior()` 已包含持续眨眼和扫视，不需要对同一角色再次调用 `enable_idle()`。
水果名称可用 `apple` / `orange` 或“苹果”/“橘子”；给孩子错误的水果会明确报错。
`mode="happy"` 或 `mode="hooray"` 仅用于明确展示某一种情况，省略时保持 50/50 随机。
已有 `place_left_hand()` 的阶段顺序、时长比例及两份目标 SVG 保留。

验证涵盖：每轮抽样与重复状态通知、正确水果规则、四人仅嘴形变化、
两个孩子在扫视途中和眨眼途中进入两种庆祝、镜像与缩放、腿部不动、
瞳孔连续衔接、恢复随机扫视、眨眼时刻与未加表情的版本一致，以及控制器停止后的清理。

## 空心水果与二维桌盘

`props.py` 直接使用 ManimGL 的 `VMobject`、`Circle`、`Line` 和 `VGroup`，
不加载或生成水果、桌盘 SVG，不依赖额外图片。

| 素材 | 默认尺寸（场景单位） | 样式 |
| --- | --- | --- |
| `AppleOutline` | 整体高 0.45、宽约 0.40 | 默认 `RED`，完整苹果轮廓加一片空心叶子，无缺口或高光 |
| `OrangeOutline` | 整体高 0.45、宽约 0.40 | 默认 `YELLOW`，圆形轮廓加短果梗 |
| `SimpleTable` | 桌面宽 1.25、高 0.80、底座宽 0.72 | 默认 `GREY_B`，三条线组成上宽下窄的工字形 |
| `OpenPlate` | 开口宽 1.15、底宽 1.0、高 0.18 | 默认 `GREY_B`，仅三个边，上方敞开的浅盘 |

线宽统一为 2.5，比 ManimGL 默认的 4 细，接近现有角色睫毛的 2.4。
水果和盘子的填充透明度为 0；所有部件都位于二维平面，没有阴影、纹理或透视。
构造器接受 `color`、`stroke_width`，水果接受 `height`，桌盘接受表内各尺寸参数。
水果保持第一版轮廓的原始宽高比例，只做等比例缩放；橘子的果身始终为圆形。

```python
from pi_family import AppleOutline, OrangeOutline, SimpleTable, OpenPlate, make_fruit_table

props = make_fruit_table()
self.add(props)
# 可单独访问 props.table、props.plate、props.apple、props.orange。
# 整组可用 Manim 的 move_to、shift、scale 等方法移动和缩放。
small_apple = AppleOutline(height=0.3, stroke_width=2.5)
```

`OpenPlate.fruit_positions()` 返回盘内两个水果的底部定位点，随盘子的移动、
缩放和镜像变化。`make_fruit_table()` 已把橘子放在左侧、苹果放在右侧，保留间隙，
对应儿子从左侧取橘子、女儿从右侧取苹果的后续布局。
这些只是图形定位点；此处没有盘子容量状态、进程或信号量。

桌盘宽度依据现有孩子的手长收窄：以预览的构造高度 1.25 为基准，
放取姿势的手端比主体向外多伸约 0.30。水果恢复原比例并缩小，同时降低桌高与盘深，
使接触位置可以位于盘沿上方。两个水果的横向间隙约 0.10，底部与盘底相隔约 0.036。
校准时保持女儿原方向，使用既有 `left_hand_place` 姿势从右侧接触苹果，
手端高度设在盘沿上方约 0.17，主体与桌边相隔约 0.10。
对既有姿势过渡共采样 84 个时刻，手臂与盘沿的最小间隙约 0.05，
手部轮廓没有进入水果内部。儿子使用相同的 Baby 手部几何，按原方向、
等价的外侧槽位检查橘子时，主体间隙同样约 0.10。
另将高度 0.45、0.35、0.25 的水果点数据逐项与第一版等比例构造结果比较，确认轮廓与比例恢复。
这次仅调整素材尺寸和槽位；角色方向、既有手臂动作及上下分区位置保持原样，
左右接近的行走和儿子的镜像留待后续场景实现。

从仓库根目录运行：

```powershell
conda activate manim
cd exp2/src
python -m pi_family.render_props_preview
manimgl pi_family/props_scene.py FruitPropsPreview
manimgl pi_family/props_scene.py FamilyTablePreview
```

导出以下本地预览，均由 ManimGL 实际渲染，生成文件被 Git 忽略：

- `preview/fruit_props.png`：1280×720 素材图，同时展示高度 0.45、0.35、0.25 的水果。
- `preview/family_table.png`：1280×720 四人围桌的二维比例示意。
- `preview/family_table_small.png`：640×360 的同一构图，便于检查缩小后的辨识度。

构图中爸爸、妈妈在上排，儿子、女儿在下排，桌盘居中，人物完整可见且互不遮挡。
预览把爸爸构造高度设为 2.4、妈妈设为 2.16、孩子设为 1.25，保留已有比例，
不更改角色类的默认尺寸或原来的动作预览。
