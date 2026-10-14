# 素材与代码来源

角色基于 3Blue1Brown 的 PiCreature。父亲使用原版 Randolph（PiCreature 的别名），
孩子使用原版 BabyPiCreature；女性角色在同一原型上加睫毛。

- `upstream/pi_creature.py`、`upstream/pi_creature_animations.py`：
  [3b1b/videos](https://github.com/3b1b/videos/tree/306a1346a356c7a7b097875ceb51c5cd67d0a56c/custom/characters)，
  快照提交 `306a1346a356c7a7b097875ceb51c5cd67d0a56c`。
  仅将这两个文件互相引用的 `custom.characters` 导入改成包内相对导入；
  PiCreature 和 BabyPiCreature 的构造与动画逻辑保留。
  授权为 CC BY-NC-SA 4.0，完整条款见 `upstream/LICENSE.txt`。
- `assets/PiCreatures_plain.svg`：
  [3b1b/manim v0.2.0](https://github.com/3b1b/manim/blob/v0.2.0/manimlib/files/PiCreatures_plain.svg)，
  未改写 SVG 路径。SHA-256：
  `5b2d1047a415b4fe153d59f8869832d652663f55db42944305090cb6b63a2395`。
  随该版本保留 MIT 授权，见 `assets/LICENSE.txt`。
- 本目录的角色适配和场景代码按 CC BY-NC-SA 4.0 提供；
  改动为六部件 SVG 索引适配、颜色、妈妈缩放，以及随眨眼变化的睫毛。
- `assets/PiCreatures_left_hand_reach.svg` 和
  `assets/PiCreatures_left_hand_place.svg` 是由 `hand_poses.py` 基于原版
  `plain` SVG 自行生成的目标姿势，不是原作者提供的姿势素材。
  只替换 `H187.4` 与 `h32.5` 之间的左手轮廓；肩部位置及其余 SVG 部件与指令保留。
  左手以原版 ManimGL 曲线细分后的节点写成二次贝塞尔曲线，轻微拉伸并抬起或放低。
  派生 SVG 保留 `assets/LICENSE.txt` 中的原版授权。

参考的原作者场景是 `3b1b/videos` 的 `_2026/2025_P6/p6.py` 中
`PiCreatureReactions`：通过 `self.play(randy.change(...))` 切换 SVG 姿势，
通过 `Blink(randy)` 眨眼。本次仅准备角色，不实现该视频的场景。

左手动作沿用原作者的 `change_mode()`：加载同类目标、匹配样式与高度、
匹配镜像方向、对齐眼睛、再由 `change()` / `play()` 插值。
本项目额外固定左手之外的所有部件和身体顶点，并使三套姿势使用同一曲线对应关系。
适配层在插值时原样保留不动的顶点，避免浮点舍入造成微小位移；
在动画结束时同步姿势名，以兼容当前 ManimGL 对已经对齐的对象跳过对齐回调的行为。
`upstream/` 中的原作者代码没有新增改动。

当前提供 `plain`、`left_hand_reach`、`left_hand_place` 三个姿势。
调用不存在的姿势会明确报错，不会用普通姿势冒充。

持续小动作参考同一提交的 `custom/characters/pi_creature_scene.py`：
原作者的 `seconds_to_blink = 3`、随机选择角色调用 `Blink`，
以及通过 `pi.animate.look_at(...)` 播放视线过渡。
本项目继续调用原版 `PiCreature.look()`、`PiCreature.blink()` 和 `Blink`，
眼睛的移动使用 Manim 的方法动画与 `smooth`，眨眼使用 `there_and_back`。
新增的独立计时、每个角色的三套扫视，以及仅作用于脸部的组合层是本项目的改动。

原作者场景的自动眨眼主要发生在 `wait()` 中；本项目通过场景时钟 updater
持续调度，使眨眼和扫视在 `wait()` 与手部 `play()` 期间都能运行。
虚拟脸部使用原版动作后将眼睛与睫毛点数据映射回角色，不写入身体或嘴巴。
开启小动作后的手部姿势准备会临时使用睁眼参考，避免闭眼改变整体边界高度
而影响原作者的姿势匹配；准备完成后恢复当前可见脸部。

眨眼间隔采用 3–5 秒随机值，均值约为每分钟 15 次，仅作为动画节奏设置。
参考 [MedlinePlus 的眨眼说明](https://www.medlineplus.gov/ency/anatomyvideos/000010.htm)。
单次 0.25 秒、扫视方向与观察幅度是本项目的动画设计参数。
