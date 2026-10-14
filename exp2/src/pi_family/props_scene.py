"""Asset and composition previews; no process synchronization logic."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manimlib import DOWN, Scene, Text, UP, VGroup
from pi_family import DaughterPi, FatherPi, MotherPi, SonPi
from pi_family.props import AppleOutline, OrangeOutline, make_fruit_table


class FruitPropsPreview(Scene):
    default_camera_config = {"background_color": "#171B23"}

    def construct(self):
        title = Text("空心水果与二维桌盘", font="Microsoft YaHei", font_size=32)
        title.move_to([0, 3.0, 0])
        apple = AppleOutline(height=1.3).move_to([-4.4, 1.3, 0])
        orange = OrangeOutline(height=1.3).move_to([-1.8, 1.3, 0])
        self.props = make_fruit_table().shift([3.0, 0.6, 0])
        self.add(title, apple, orange, self.props)
        for name, x in (("苹果", -4.4), ("橘子", -1.8), ("桌子与双水果盘", 3.0)):
            self.add(Text(name, font="Microsoft YaHei", font_size=24)
                     .move_to([x, -0.7, 0]))
        # Render at their actual small sizes, rather than downsampling an image.
        for index, height in enumerate((0.45, 0.35, 0.25)):
            pair = VGroup(AppleOutline(height=height), OrangeOutline(height=height))
            pair.arrange(buff=0.22).move_to([-3.6 + 3.6 * index, -2.0, 0])
            label = Text(f"高度 {height:.2f}", font="Microsoft YaHei", font_size=22)
            label.move_to([-3.6 + 3.6 * index, -2.75, 0])
            self.add(pair, label)


class FamilyTablePreview(Scene):
    default_camera_config = {"background_color": "#171B23"}

    def construct(self):
        father, mother = FatherPi(height=2.4), MotherPi(height=2.16)
        son, daughter = SonPi(height=1.25), DaughterPi(height=1.25)
        self.family = VGroup(father, mother, son, daughter)
        self.props = make_fruit_table().shift(0.15 * DOWN)
        for pi, x, body_bottom in (
            (father, -2.7, 1.15), (mother, 2.7, 1.15),
            (son, -2.7, -2.75), (daughter, 2.7, -2.75),
        ):
            pi.set_x(x)
            pi.shift((body_bottom - pi.body.get_bottom()[1]) * UP)
        self.add(self.props, self.family)
        for name, pi, y in (
            ("爸爸", father, 0.86), ("妈妈", mother, 0.86),
            ("儿子", son, -3.1), ("女儿", daughter, -3.1),
        ):
            self.add(Text(name, font="Microsoft YaHei", font_size=23,
                          color=pi.get_color()).move_to([pi.get_x(), y, 0]))
