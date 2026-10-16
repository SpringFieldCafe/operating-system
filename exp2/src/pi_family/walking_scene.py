"""Four role demos with real hand/fruit transfers; no synchronization policy."""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manimlib import Line, Scene, Text
from pi_family import carry_fruit, enable_behavior, hand_tip, place_hand, standing_point, take_hand, walk_to
from pi_family.contact_layout import CONTACT_ROLES, make_contact_pose


class _WalkingRoleDemo(Scene):
    default_camera_config = {"background_color": "#000000"}
    role_key = "father"
    behavior_seed = 43

    def caption(self, text):
        if hasattr(self, "status_caption"):
            self.remove(self.status_caption)
        self.status_caption = Text(text, font="Microsoft YaHei", font_size=22).move_to([0, -1.95, 0])
        self.add(self.status_caption)

    def mark(self, phase):
        pass

    def construct(self):
        role = CONTACT_ROLES[self.role_key]
        pi, props = make_contact_pose(self.role_key)
        self.character, self.props = pi, props
        fruit = getattr(props, role.fruit)
        destination = standing_point(pi).copy()
        contact_offset = fruit.get_center() - hand_tip(pi, role.hand)
        pi.change_mode("plain")
        home = destination + np.array([role.side * 2.0, 0, 0])
        pi.shift(home - standing_point(pi))
        parent = self.role_key in ("father", "mother")
        if parent:
            carry_fruit(pi, fruit, hand=role.hand, offset=contact_offset)
        self.camera.frame.set_width(10).move_to([0, 0.65, 0])
        hand_name = "左手" if role.hand == "left" else "右手"
        title = Text(f"{role.label} · {role.action} · {hand_name}", font="Microsoft YaHei",
                     font_size=27, color=pi.get_color()).move_to([0, 2.65, 0])
        floor = Line([-4.7, destination[1] - 0.02, 0], [4.7, destination[1] - 0.02, 0],
                     stroke_color="#333B48", stroke_width=1)
        self.add(floor, props, pi, title)
        self.behavior = enable_behavior(self, pi, seed=self.behavior_seed)
        self.caption("走近桌子 · 双腿交替小步")
        self.wait(0.4)
        self.mark("start")
        walk_to(self, pi, destination, run_time=2.4)
        self.mark("arrived")
        self.wait(0.25)
        self.caption(f"站稳后{role.action} · 另一只手保持不动")
        if parent:
            place_hand(self, pi, hand=role.hand, fruit=fruit, run_time=1.8)
            self.behavior.parent_placed(pi)
        else:
            take_hand(self, pi, hand=role.hand, fruit=fruit, run_time=1.8)
        self.mark("transferred")
        if not parent:
            self.behavior.child_received(pi, role.fruit, look_target=fruit,
                                         mode="hooray" if self.role_key == "son" else "happy")
        self.caption("完成取放 · 表情与眨眼连续衔接")
        self.wait(1.95)
        self.mark("celebrated")
        self.caption("空手返程" if parent else "持果手稳定 · 空手轻摆 · 返程")
        walk_to(self, pi, home, run_time=2.4)
        self.mark("returned")
        self.wait(0.55)


class FatherWalkingDemo(_WalkingRoleDemo):
    role_key = "father"


class MotherWalkingDemo(_WalkingRoleDemo):
    role_key = "mother"


class SonWalkingDemo(_WalkingRoleDemo):
    role_key = "son"


class DaughterWalkingDemo(_WalkingRoleDemo):
    role_key = "daughter"
