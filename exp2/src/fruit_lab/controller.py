"""Commands shared by the real IPython session and render verification."""

import json
import math
from pathlib import Path

from .engine import ProcessLab
from .visuals import Presentation

DEMOS = {
    "empty": dict(son=1),
    "full": dict(father=3),
    "types": dict(father=1, son=1),
    "wakeup": dict(daughter=1, father=1),
    "mutex": dict(father=1, mother=1),
    "concurrent": dict(father=3, mother=3, son=3, daughter=3),
    "unbalanced": dict(father=4, daughter=1),
}


class LabController:
    def __init__(self, scene):
        self.scene = scene
        self.business_time = self.ambient_time = 0.0
        self.paused = self.stepping = self.detailed = False
        self.rate = 1.0
        self.reset_pending = False
        self.pending_demo = None
        self.history = []
        self.failure = None
        self.closed = False
        self.engine = ProcessLab()
        try:
            self.presentation = Presentation(scene, self)
        except BaseException:
            self.engine.close()
            raise
        self.epoch = self.engine.snapshot()["epoch"]
        self.presentation.hud(self.engine.snapshot())

    def _check(self):
        if self.closed or self.failure:
            raise RuntimeError(self.failure or "The lab is closed.")

    def tick(self, dt):
        if self.closed or self.failure:
            return
        self.ambient_time += dt
        try:
            for event in self.engine.poll():
                self.history.append(dict(event, time=round(self.business_time, 4)))
                if event["epoch"] != self.epoch:
                    continue
                if event["kind"] == "error":
                    raise RuntimeError(event["message"])
                if event["kind"] == "released" and event.get("step"):
                    self.stepping = False
                self.presentation.on_event(event)
                # Consume acknowledgment boundaries before a following grant
                # for that same role can create its next track.
                self.presentation.tick(0)
            business_dt = dt * self.rate if not self.paused or self.stepping else 0
            self.business_time += business_dt
            self.presentation.tick(business_dt)
            snapshot = self.engine.snapshot()
            self.presentation.hud(snapshot)
            if self.reset_pending and not self.presentation.tracks and not any(v["active"] for v in snapshot["roles"].values()):
                self._complete_reset()
        except Exception as exc:
            self.failure = f"{type(exc).__name__}: {exc}"
            self.paused, self.stepping = True, False
            # The live scene owns diagnostics and process cleanup. Do not try
            # to construct more graphics while handling a failing frame.
            raise

    def submit(self, role, count=1):
        self._check()
        self.engine.submit(role, count)

    def batch(self, **counts):
        self._check()
        self.engine.submit_many(**counts)

    def cancel(self, role=None):
        self._check()
        self.engine.cancel(role)

    def pause(self):
        self._check()
        if self.reset_pending:
            raise RuntimeError("正在收尾重置，请等重置完成后暂停。")
        self.engine.pause()
        self.paused, self.stepping = True, False

    def resume(self):
        self._check()
        self.engine.resume()
        self.paused = self.stepping = False

    def step(self):
        self._check()
        if self.reset_pending:
            raise RuntimeError("正在收尾重置，请等重置完成后单步。")
        self.engine.step()
        self.paused, self.stepping = True, True

    def speed(self, factor=1.0):
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor) or not 0.25 <= factor <= 4:
            raise ValueError("Speed must be a finite number between 0.25 and 4.")
        self.rate = float(factor)

    def detail(self, enabled=True):
        if not isinstance(enabled, bool):
            raise ValueError("Use detail(True) or detail(False).")
        self.detailed = enabled

    def reset(self):
        self._schedule_reset(None)

    def demo(self, name="concurrent"):
        if name not in DEMOS:
            raise ValueError("Choose a demo from: " + ", ".join(DEMOS))
        self._schedule_reset(name)

    def _schedule_reset(self, demo):
        self._check()
        if self.reset_pending:
            raise RuntimeError("已有一次重置正在收尾；请等它完成后再切换。")
        self.engine.prepare_reset()
        self.paused = self.stepping = False
        self.reset_pending = True
        self.pending_demo = demo

    def _complete_reset(self):
        semaphores = self.presentation.semaphores
        self.presentation.close()
        self.scene.clear()
        snapshot = self.engine.reset()
        self.epoch = snapshot["epoch"]
        self.business_time = self.ambient_time = 0.0
        self.reset_pending = False
        name, self.pending_demo = self.pending_demo, None
        if name is None:
            self.rate = 1.0
        self.presentation = Presentation(self.scene, self, semaphores=semaphores)
        self.presentation.hud(snapshot)
        if name is not None:
            self.engine.submit_many(**DEMOS[name])

    def status(self):
        self._check()
        self.engine.snapshot()

    def events(self, count=12):
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
            raise ValueError("Use an integer count between 1 and 1000.")

    def save_log(self, filename=None):
        self._check()
        path = Path(filename) if filename is not None else Path(__file__).resolve().parents[2] / "report" / "fruit_lab_session.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(snapshot=self.engine.snapshot(), events=self.history), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def help_cmds():
        """Keep the command available for completion without terminal output."""

    def close(self):
        if not self.closed:
            try:
                self.presentation.close()
            finally:
                self.engine.close()
                self.closed = True
