"""Four-character facial asset preview; all waiting states are manual cues."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pi_family import enable_behavior
from pi_family.preview_scene import FamilyExpressionDemo, FamilyPortrait


class FamilyAngryDemo(FamilyExpressionDemo):
    reaction_seed = 12

    def mark(self, phase):
        pass

    def statuses(self, text):
        for pi in self.family:
            self.status(pi, text)

    def construct(self):
        FamilyPortrait.construct(self)
        self.role_status = [None]*4
        self.behavior = enable_behavior(self, self.family, seed=self.reaction_seed)
        self.behavior.prepare_angry_faces()
        self.caption("四个角色的等待表情 · 素材预览")
        self.statuses("正常 / 浅笑")
        self.wait(0.6)
        self.mark("ready")
        for pi in self.family:
            self.behavior.waiting(pi)
        self.caption("短暂等待 · 轻微撇嘴")
        self.statuses("等待 · 撇嘴")
        self.wait(1.0)
        self.mark("waiting")
        self.wait(1.5)
        self.caption("持续等待 · 逐渐生气 · 眼部与嘴形一起变化")
        self.statuses("等待 · 愤怒")
        self.wait(1/24)
        # Capture after the first blinks have reopened, so the still shows
        # all four reference eye silhouettes clearly. Blink timing is intact.
        self.wait(2.5)
        self.mark("angry")
        self.wait(0.7)
        for pi in self.family:
            self.behavior.ready(pi)
        self.caption("等待结束 · 平滑恢复 · 眨眼和扫视持续")
        self.statuses("恢复正常 / 浅笑")
        self.wait(0.6)
        self.mark("recovered")
        for pi in self.family:
            self.behavior.waiting(pi)
        self.caption("再次短暂等待 · 不会立即生气")
        self.statuses("短暂等待 · 撇嘴")
        self.wait(1.2)
        for pi in self.family:
            self.behavior.ready(pi)
        self.caption("短暂等待已结束 · 保持原来的角色姿势")
        self.statuses("正常 / 浅笑")
        self.wait(0.6)
        self.mark("short_wait_finished")
