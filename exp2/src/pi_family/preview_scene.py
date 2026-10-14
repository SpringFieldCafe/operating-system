"""Static character sheet and a short gaze/blink preview, with no lab logic."""

from pathlib import Path
import sys

# ManimGL loads scene files directly; make the package importable from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manimlib import LEFT, RIGHT, UP, LaggedStart, Scene, Text, VGroup
from pi_family import Blink, enable_idle, enable_behavior, make_family, place_left_hand, take_left_hand


class FamilyPortrait(Scene):
    default_camera_config = {"background_color": "#171B23"}

    def construct(self):
        self.family = make_family()
        names = ("爸爸", "妈妈", "儿子", "女儿")
        labels = VGroup(*[
            Text(name, font="Microsoft YaHei", font_size=28, color=pi.get_color())
            .move_to([pi.get_x(), -1.95, 0])
            for name, pi in zip(names, self.family)
        ])
        self.add(self.family, labels)


class FamilyMotion(FamilyPortrait):
    def construct(self):
        super().construct()
        self.wait(0.4)
        self.play(*[pi.animate.look(UP + LEFT) for pi in self.family], run_time=0.8)
        self.play(LaggedStart(*[Blink(pi) for pi in self.family], lag_ratio=0.25), run_time=0.9)
        self.play(*[pi.animate.look(RIGHT) for pi in self.family], run_time=0.8)
        self.play(*[pi.animate.look(LEFT) for pi in self.family], run_time=0.8)
        self.wait(0.6)


class LeftHandPlacementDemo(FamilyPortrait):
    def construct(self):
        super().construct()
        self.wait(0.5)
        place_left_hand(self, self.family, run_time=2.0)
        self.wait(0.6)


class FamilyIdleDemo(FamilyPortrait):
    idle_seed = None

    def construct(self):
        super().construct()
        self.idle = enable_idle(self, self.family, seed=self.idle_seed)
        self.wait(4.0)
        place_left_hand(self, self.family, run_time=2.0)
        self.wait(7.0)


class FamilyExpressionDemo(FamilyPortrait):
    """A character/state preview, not a simulated concurrent fruit program."""
    reaction_seed = None

    def caption(self, text):
        if hasattr(self, "status_caption"):
            self.remove(self.status_caption)
        self.status_caption = Text(text, font="Microsoft YaHei", font_size=25).move_to([0, 2.65, 0])
        self.add(self.status_caption)

    def status(self, pi, text):
        index = list(self.family).index(pi)
        if self.role_status[index] is not None:
            self.remove(self.role_status[index])
        label = Text(text, font="Microsoft YaHei", font_size=20, color=pi.get_color()).move_to([pi.get_x(), -2.5, 0])
        self.role_status[index] = label
        self.add(label)

    def parent_status(self, pi):
        expression = "浅笑" if self.behavior.get_expression(pi) == "parent_smile" else "正常"
        self.status(pi, f"可操作 · {expression}")

    def collect(self, pi, fruit):
        self.behavior.ready(pi)
        self.caption(f"取回{fruit}以后，随机选择开心或欢呼")
        self.status(pi, f"取回{fruit}")
        take_left_hand(self, pi, run_time=1.6)
        mode = self.behavior.child_received(pi, fruit)
        self.status(pi, "开心" if mode == "happy" else "欢呼")
        self.wait(self.behavior.reaction_settings.celebration_duration + 0.15)
        self.status(pi, "恢复正常 · 随机扫视")

    def construct(self):
        super().construct()
        self.family[3].flip()
        self.role_status = [None] * 4
        father, mother, son, daughter = self.family
        self.behavior = enable_behavior(self, self.family, seed=self.reaction_seed)
        self.caption("角色动作预览：可操作时正常或浅笑")
        self.parent_status(father)
        self.parent_status(mother)
        for pi, fruit in ((son, "橘子"), (daughter, "苹果")):
            self.behavior.waiting(pi)
            self.status(pi, f"等待{fruit}")
        self.wait(1.3)
        for pi, fruit in ((father, "苹果"), (mother, "橘子")):
            self.caption(f"放{fruit}：保留原来的左手动作")
            self.status(pi, f"放{fruit}")
            place_left_hand(self, pi)
            self.behavior.parent_placed(pi)
            self.parent_status(pi)
        self.collect(son, "橘子")
        self.collect(daughter, "苹果")
        self.caption("父母阻塞等待时，只轻微撇嘴")
        for pi in (father, mother):
            self.behavior.waiting(pi)
            self.status(pi, "阻塞等待 · 撇嘴")
        self.wait(1.6)
        for pi in (father, mother):
            self.behavior.ready(pi)
            self.parent_status(pi)
        self.collect(son, "橘子")
        self.collect(daughter, "苹果")
        self.caption("四个角色的等待嘴形（状态示意）")
        for pi in self.family:
            self.behavior.waiting(pi)
            self.status(pi, "等待 · 轻微撇嘴")
        self.wait(1.6)
        for pi in self.family:
            self.behavior.ready(pi)
        self.caption("恢复可操作：眨眼与扫视继续独立运行")
        self.parent_status(father)
        self.parent_status(mother)
        for pi in (son, daughter):
            self.status(pi, "正常 · 随机扫视")
        self.wait(1.5)
