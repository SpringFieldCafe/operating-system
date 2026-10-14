"""Static character sheet and a short gaze/blink preview, with no lab logic."""

from pathlib import Path
import sys

# ManimGL loads scene files directly; make the package importable from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manimlib import LEFT, RIGHT, UP, LaggedStart, Scene, Text, VGroup
from pi_family import Blink, make_family


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
