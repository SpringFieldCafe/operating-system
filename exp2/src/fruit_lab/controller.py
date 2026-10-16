"""Commands shared by the real IPython session and render verification."""

import json
import math
from pathlib import Path

from .engine import LABELS, ROLES, ProcessLab
from .visuals import Presentation

DEMOS = {
    "empty": (dict(son=1), "儿子等待橘子；输入 mother(1) 可解除等待。"),
    "full": (dict(father=3), "两个苹果放满后爸爸等待；输入 daughter(3) 可完成全部请求。"),
    "types": (dict(father=1, son=1), "有苹果仍不能满足儿子；输入 mother(1) 让儿子取得橘子。"),
    "wakeup": (dict(daughter=1, father=1), "女儿先等苹果；爸爸放入后唤醒，取果返回再庆祝。"),
    "mutex": (dict(father=1, mother=1), "父母竞争同一盘子的操作权；两种水果都可留在盘中。"),
    "concurrent": (dict(father=3, mother=3, son=3, daughter=3), "四个角色真实竞争，最终请求配平、盘子清空。"),
    "unbalanced": (dict(father=4, daughter=1), "取果次数不足，留下两个苹果和一次待办；这是资源等待。"),
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
        snapshot = self.engine.submit(role, count)
        info = snapshot["roles"][role]
        print(f"{LABELS[ROLES.index(role)]}：追加 {count} 次，待办 {info['pending']} 次；正在进行的一趟另计。")

    def batch(self, **counts):
        self._check()
        self.engine.submit_many(**counts)
        print("已同时提交：" + "、".join(f"{LABELS[ROLES.index(r)]} {n} 次" for r, n in counts.items()))

    def cancel(self, role=None):
        self._check()
        before = self.engine.snapshot()
        self.engine.cancel(role)
        indices = ROLES if role is None else (role,)
        print("已撤回未出发请求：" + "、".join(f"{LABELS[ROLES.index(r)]} {before['roles'][r]['pending']} 次" for r in indices)
              + "；已出发的一趟继续完成。")

    def pause(self):
        self._check()
        if self.reset_pending:
            raise RuntimeError("正在收尾重置，请等重置完成后暂停。")
        self.engine.pause()
        self.paused, self.stepping = True, False
        print("已暂停业务与动作；云朵、眨眼、扫视继续。")

    def resume(self):
        self._check()
        self.engine.resume()
        self.paused = self.stepping = False
        print("继续运行。")

    def step(self):
        self._check()
        if self.reset_pending:
            raise RuntimeError("正在收尾重置，请等重置完成后单步。")
        self.engine.step()
        self.paused, self.stepping = True, True
        print("单步：放行一次取放，完成必要整理并释放盘子后停下；若资源不足，等待补充请求。")

    def speed(self, factor=1.0):
        if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor) or not 0.25 <= factor <= 4:
            raise ValueError("Speed must be a finite number between 0.25 and 4.")
        self.rate = float(factor)
        print(f"业务动画速度：{self.rate:g}×；资源条件与互斥规则保持有效。")

    def detail(self, enabled=True):
        if not isinstance(enabled, bool):
            raise ValueError("Use detail(True) or detail(False).")
        self.detailed = enabled
        self.presentation.set_detail(enabled)
        print("已切换到" + ("详细同步讲解。" if enabled else "简洁展示。"))

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
        print("已撤回未出发请求；已出发动作完成后自动清空归位。")

    def _complete_reset(self):
        self.presentation.close()
        self.scene.clear()
        snapshot = self.engine.reset()
        self.epoch = snapshot["epoch"]
        self.business_time = self.ambient_time = 0.0
        self.reset_pending = False
        name, self.pending_demo = self.pending_demo, None
        if name is None:
            self.rate = 1.0
        self.presentation = Presentation(self.scene, self)
        if name is not None:
            counts, explanation = DEMOS[name]
            self.engine.submit_many(**counts)
            self.presentation.say_caption("演示：" + name)
            print(f"demo({name!r})：{explanation}")
        else:
            print("重置完成：空盘、四人归位、请求与计数清零、速度恢复 1×。")

    def status(self):
        self._check()
        s = self.engine.snapshot()
        names = {None: "空", "apple": "苹果", "orange": "橘子"}
        print("盘内：" + "、".join(names[v] for v in s["slots"]))
        print(f"状态：{'暂停' if self.paused else '运行'}，速度 {self.rate:g}×，操作权：{s['owner'] or '空闲'}")
        print("角色       待办  进行中  完成  已取消   PID     原因/阶段")
        for i, role in enumerate(ROLES):
            v = s["roles"][role]
            print(f"{LABELS[i]:<8} {v['pending']:>4} {int(v['active']):>6} {v['completed']:>5} {v['cancelled']:>6} {v['pid']:>7}   "
                  f"{self.presentation.phases[role] if v['active'] else v['reason']}")

    def events(self, count=12):
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
            raise ValueError("Use an integer count between 1 and 1000.")
        for e in self.history[-count:]:
            print(f"#{e['seq']} epoch={e['epoch']} t={e['time']:.2f} {e.get('role') or '-'}: {e['kind']} "
                  + str(e.get("reason") or ", ".join(e.get("operations", []))))

    def save_log(self, filename=None):
        self._check()
        path = Path(filename) if filename is not None else Path(__file__).resolve().parents[2] / "report" / "fruit_lab_session.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(snapshot=self.engine.snapshot(), events=self.history), ensure_ascii=False, indent=2), encoding="utf-8")
        print("已保存实验事件记录。")

    @staticmethod
    def help_cmds():
        print("""角色命令（次数为正整数，重复输入会追加）：
  father(3)   mother(2)   son(2)   daughter(3)
  batch(father=3, mother=3, son=3, daughter=3)
控制：
  cancel('father')   cancel()   status()
  pause()   resume()   step()   speed(2)   detail(True)
  reset()   events(12)   save_log()   exit()
典型场景（自动收尾并从空盘开始）：
  demo('empty')        缺橘子；用 mother(1) 唤醒
  demo('full')         两个苹果放满；用 daughter(3) 完成
  demo('types')        苹果不能满足儿子；用 mother(1) 解除
  demo('wakeup')       女儿等待、爸爸放入、女儿取回
  demo('mutex')        父母争用盘子，展示互斥
  demo('concurrent')   四角色各三次，真实并发与配平
  demo('unbalanced')   次数不匹配；用 daughter(3) 完成
单步在一次取放及必要整理完成并释放操作权后停下，剩余返程可在下一步或 resume() 时继续。
等待原因气泡会保留到等待解除；等待满两秒逐渐愤怒。
""")

    def close(self):
        if not self.closed:
            try:
                self.presentation.close()
            finally:
                self.engine.close()
                self.closed = True
