"""Exercise commands, all presets, geometry, cancellation and live pause clocks."""

from pathlib import Path
import sys
import time


def main():
    geometry_only = "--geometry-only" in sys.argv
    sys.argv[:] = [sys.argv[0]]
    import numpy as np
    from .scene import FruitLabScene
    scene = FruitLabScene(camera_config={"resolution": (1280, 720), "fps": 30})
    output = Path(__file__).resolve().parents[1] / "pi_family" / "preview"
    try:
        scene.build_lab()
        lab = scene.lab

        def drive(predicate, limit=30):
            deadline = time.monotonic() + limit
            while time.monotonic() < deadline:
                lab.tick(0.06)
                snapshot = lab.engine.snapshot()
                if predicate(snapshot):
                    return snapshot
                time.sleep(0.001)  # Let actual spawned workers receive IPC acknowledgments.
            raise AssertionError((lab.engine.snapshot(), lab.presentation.phases))

        def complete(s, role, count):
            return s["roles"][role]["completed"] == count and not s["roles"][role]["active"]

        def stable_geometry():
            p = lab.presentation
            for slot, fruit in p.plate_fruits.items():
                attachment = getattr(fruit, "_hand_attachment", None)
                assert attachment is None or not attachment.active
                expected = p.positions[0][1]
                actual_bottom = fruit.get_all_points()[:, 1].min()
                assert abs(actual_bottom - expected) < 0.035, (slot, actual_bottom, p.positions)
                assert abs(actual_bottom - fruit.get_bottom()[1]) < 0.002

        def capture(name):
            scene.update_frame(0, force_draw=True)
            scene.get_image().save(output / (name + ".png"))

        lab.demo("full")
        drive(lambda s: complete(s, "father", 2) and s["roles"]["father"]["reason"] == "space")
        stable_geometry()
        lab.tick(2.5)
        capture("lab_full")
        if geometry_only:
            print("GEOMETRY_OK: two real apple outlines above the plate floor; point/bounds agreement", flush=True)
            return
        before = lab.business_time
        lab.pause()
        anger = [c.anger for c in lab.presentation.behavior.controllers]
        eye_times = [c.last_time for c in lab.presentation.behavior.controllers]
        lab.tick(1)
        assert lab.business_time == before
        assert anger == [c.anger for c in lab.presentation.behavior.controllers]
        assert all(c.last_time > t for c, t in zip(lab.presentation.behavior.controllers, eye_times))
        assert "father" in lab.presentation.bubbles
        lab.resume()
        lab.submit("daughter", 3)
        drive(lambda s: complete(s, "daughter", 3))

        lab.demo("empty")
        drive(lambda s: not lab.reset_pending and s["roles"]["son"]["reason"] == "orange")
        lab.submit("mother")
        drive(lambda s: complete(s, "son", 1))

        lab.demo("types")
        drive(lambda s: not lab.reset_pending and complete(s, "father", 1) and s["roles"]["son"]["reason"] == "orange")
        assert "apple" in lab.engine.snapshot()["slots"]
        lab.submit("mother")
        drive(lambda s: complete(s, "son", 1))

        lab.demo("wakeup")
        drive(lambda s: not lab.reset_pending and complete(s, "daughter", 1))

        lab.demo("mutex")
        drive(lambda s: not lab.reset_pending and complete(s, "father", 1) and complete(s, "mother", 1))
        stable_geometry()
        assert any(e["kind"] == "state" and e.get("reason") == "mutex" for e in lab.history)

        lab.demo("concurrent")
        drive(lambda s: not lab.reset_pending and all(complete(s, r, 3) for r in s["roles"]), limit=60)
        assert lab.engine.snapshot()["slots"] == [None, None]

        lab.demo("unbalanced")
        drive(lambda s: not lab.reset_pending and complete(s, "father", 3) and complete(s, "daughter", 1))
        assert lab.engine.snapshot()["roles"]["father"]["pending"] == 1
        lab.cancel("father")
        drive(lambda s: s["roles"]["father"]["reason"] == "idle")

        # Reset while an actor has already departed: that trip must finish.
        lab.demo("concurrent")
        drive(lambda s: not lab.reset_pending and any(p == "outbound" for p in lab.presentation.phases.values()))
        prior_epoch = lab.epoch
        lab.demo("empty")
        drive(lambda s: lab.epoch > prior_epoch and not lab.reset_pending and s["roles"]["son"]["reason"] == "orange")
        lab.cancel()
        lab.reset()
        drive(lambda s: not lab.reset_pending and all(not v["active"] for v in s["roles"].values()))
        lab.pause()
        lab.batch(father=1, daughter=1)
        drive(lambda s: s["roles"]["father"]["reason"] == "paused")
        baseline = len([e for e in lab.history if e["epoch"] == lab.epoch and e["kind"] == "committed"])
        lab.step()
        drive(lambda s: not lab.stepping)
        assert len([e for e in lab.history if e["epoch"] == lab.epoch and e["kind"] == "committed"]) == baseline + 1
        assert lab.paused
        lab.resume()
        drive(lambda s: complete(s, "father", 1) and complete(s, "daughter", 1))
        lab.save_log()
        print("SCENARIOS_OK all seven presets; reset in flight; cancel; step; paused gaze; plate geometry", flush=True)
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
