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

最初的手部 `change()` 接口提供 `plain`、`left_hand_reach`、`left_hand_place` 三个姿势；
新增的右手和持果姿势见本文末尾。
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

## 表情与欢呼参考

- 开心与欢呼的公开收藏副本来自
  [CaftBotti/manim_pi_creatures](https://github.com/CaftBotti/manim_pi_creatures/tree/6a5babc6518d7d7e604c503db98abdbb269d087e/PiCreature)，
  固定提交 `6a5babc6518d7d7e604c503db98abdbb269d087e`。
  收藏仓库 README 声明其 `PiCreature/` 文件来自原作者网站。
  原网站旧链接在此次核对时返回 404，因此这里注明为公开收藏副本，
  不保证与最新视频的内部素材完全同版。
- `PiCreatures_happy.svg` SHA-256：
  `bf4f55a7ad22b710317672db13436cc2da3f99d66b9367f8817768cfe80e6ecd`。
- `PiCreatures_hooray.svg` SHA-256：
  `eb0553be9a962a8f8db910f3057ad3e7d824c4066e22c7b6d9dba3d973be5bf7`。
- 原始收藏副本由 `expression_assets.py` 按固定地址下载并核验，仅存入被 Git 忽略的
  `assets/reference/`，不纳入此仓库的发布内容。这里没有将它们重新授权为 MIT。
  原作者说明角色设计的权益与 Manim 的软件许可分开，见
  [原作者的说明](https://github.com/3b1b/manim/issues/18#issuecomment-1501234962)。

本项目读取这两个 SVG 的嘴部路径；欢呼同时读取身体路径中的手部变化。
开心的身体与正常轮廓相同，仅有整体 SVG 坐标偏移及细小导出舍入差异，因此保留正常身体。
欢呼的坐标以同一腿部连接点对齐；复用正常轮廓的曲线细分分配，使对应顶点一致，
并保留原有腿部顶点。眼睛不从表情 SVG 重建，现有 Baby 比例与睫毛保留。

`expression_geometry.py` 的曲线细分分配适配自 ManimGL 的
`VMobject.insert_n_curves_to_point_list()`，使用本地引擎版本 `fafa083` 的算法，
遵循 MIT 许可；完整许可保存在 `upstream/MANIM_LICENSE.txt`。
其余角色状态调度、关注水果并恢复扫视的切换、独立随机抽样及连续组合层由本项目编写。
`upstream/` 中两份 PiCreature 作者代码保持原样。

`assets/PiCreatures_parent_smile.svg`、`assets/PiCreatures_waiting.svg` 由本项目绘制嘴巴，
仅替换旧版正常 SVG 的嘴部路径。其他五条路径与原稿相同，保留旧版素材的 MIT 许可。

## 水果与桌盘

`props.py` 的苹果、橘子、桌子和盘子由本项目用 ManimGL 原生曲线、圆与直线绘制。
苹果采用完整果身与单叶的简化轮廓，没有使用或描摹外部 logo 路径。
这些素材不加载、不生成独立 SVG，也不包含图片或下载依赖。
`props_scene.py` 与 `render_props_preview.py` 提供素材大小及上下分区构图的实际渲染预览。
新增代码沿用本目录的 CC BY-NC-SA 4.0 授权。

`contact_layout.py` 用实际 ManimGL 曲线采样计算四个角色的接触位置，
`render_contact_previews.py` 与 `verify_contact_fit.py` 提供同尺度对比图和姿势过渡检查。
四个角色保持同一造型方向，左侧妈妈、儿子使用新增的右手姿势，右侧爸爸、女儿使用左手。
原始正常 SVG、最初两张左手目标 SVG 和作者的 `upstream/` 代码保留。

## 双手与走路

`PiCreatures_right_hand_reach.svg`、`PiCreatures_right_hand_place.svg` 与左右 `hand_hold` SVG
由本项目在旧版正常 SVG 上派生，使用 `hand_poses.py` 生成。仅改动各自的手臂区间，
保留原版其他五条路径、双腿、肩部连接点和切线；右手没有使用镜像的左手轮廓。
这些派生 SVG 保留 `assets/LICENSE.txt` 的原版 MIT 授权。

曾核对原作者旧版
[WalkPiCreature](https://github.com/3b1b/manim/blob/400aa0aada85a39b5f1fafa1c5572af17165047f/animation/simple_animations.py#L137-L157)
及
[get_step_intermediate](https://github.com/3b1b/manim/blob/400aa0aada85a39b5f1fafa1c5572af17165047f/mobject/creatures.py#L137-L151)，
以及 `3b1b/videos/_2015/eulers_characteristic_formula.py` 的 `WalkingRandolph` 场景。
本项目借鉴双腿局部变形与角色移动组合的思路，未导入或复制早期 PNG 部件、Python 2 动画类。
`walking.py` 的支撑/抬脚周期、按距离推进、起停收敛、身体起伏及空手摆动由本项目编写，
继续使用当前 ManimGL 的 `Animation`、`smooth` 和既有 SVG 顶点。

作者的 `WaveArm` 将单手动作与走路分开；`_2018/eop/bayes.py` 中将吉他与手臂加入角色，
使道具跟随整体变换。本项目的 `carrying.py` 使用独立水果 updater 跟随当前手端，
不将水果加入角色边界框；这套取放、持果、表情衔接和角色行为组合属于本项目实现，
不称作原作者现成的持物走路代码。新增 Python 代码沿用本目录 CC BY-NC-SA 4.0 授权。

## 愤怒表情

原作者的视频代码使用 `angry` 模式，例如
[`_2026/hairy_ball/supplements.py`](https://github.com/3b1b/videos/blob/306a1346a356c7a7b097875ceb51c5cd67d0a56c/_2026/hairy_ball/supplements.py#L485)。
本项目的具体参考素材来自同一个公开收藏副本：
[`PiCreatures_angry.svg`](https://github.com/CaftBotti/manim_pi_creatures/blob/6a5babc6518d7d7e604c503db98abdbb269d087e/PiCreature/PiCreatures_angry.svg)，
SHA-256 为 `baeb224f6b4dc62f7defa04e07998f2d6c76c48652bdb012ec0cdc787a61d4ca`。
收藏者声明其 `PiCreature/` 素材来自原作者网站；不保证这一副本与最新视频内部素材同版。
它与开心、欢呼参考一样，仅下载到被 Git 忽略的 `assets/reference/`，不随项目发布，
不重新授权为 MIT。

`expression_geometry.py` 提取参考的皱嘴和两只眼部轮廓。
`angry_face.py` 将轮廓按各自原有眼宽与眼底定位，对齐闭合曲线的方向和起点后平滑变形，
保留 Baby 大眼比例与瞳孔尺寸，让睫毛随眼沿移动，并约束瞳孔位置。
`idle_motion.py` 先沿用作者的视线计算，再合成这层眼形，最后叠加原作者的 `Blink`；
没有改写 `upstream/` 中的作者代码。

等待满 2 秒后再逐渐生气、0.4 秒的眼口过渡、重复等待通知的去重、平滑恢复，以及
`angry_scene.py` 的四人素材预览均为本项目的行为设计，不称作原作者的调度或等待实现。
这些代码不管理进程和资源，身体、手臂、双腿与已有持果关系仍由现有动画负责。
