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

参考的原作者场景是 `3b1b/videos` 的 `_2026/2025_P6/p6.py` 中
`PiCreatureReactions`：通过 `self.play(randy.change(...))` 切换 SVG 姿势，
通过 `Blink(randy)` 眨眼。本次仅准备角色，不实现该视频的场景。

当前仅随项目提供公开的 `plain` SVG。其他姿势需要额外的原作者素材；
调用不存在的姿势会明确报错，不会用普通姿势冒充。视线、移动、缩放、翻转和眨眼
均可使用，不依赖其他 SVG。
