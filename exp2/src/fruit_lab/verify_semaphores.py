"""Check native permit values, fixed TeX geometry, transitions and clearance."""

import argparse
from pathlib import Path
import sys
import time


OUTPUT = Path(__file__).resolve().parents[3] / ".privacy-review" / "semaphores"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    sys.argv[:] = [sys.argv[0]]
    import numpy as np
    from manimlib import Text
    from .scene import FruitLabScene

    scene = FruitLabScene(camera_config={"fps": 30})
    frames = []
    samples = 0
    try:
        scene.build_lab()
        lab = scene.lab
        display = lab.presentation.semaphores
        low = display.bounds[:, :2].min(axis=0)
        high = display.bounds[:, :2].max(axis=0)
        assert abs((low[0] + high[0]) / 2) < 1e-6
        assert low[1] > 2.3 and high[1] < 4.3, (low, high)
        assert np.ptp([anchor[0] for anchor in display.anchors]) < 0.01
        if args.render:
            OUTPUT.mkdir(parents=True, exist_ok=True)

        def capture(name=None, animation=False):
            if not args.render:
                return
            scene.camera.capture(*scene.mobjects)
            image = scene.get_image()
            if name:
                image.save(OUTPUT / (name + ".png"))
            if animation:
                frames.append(image.crop((560, 35, 880, 230)).resize((640, 390)))

        def check_clearance():
            nonlocal samples
            view = lab.presentation
            for name, item in [*view.actors.items(), *view.bubbles.items(), *view.carried.items()]:
                points = item.get_all_points()
                if not len(points):
                    continue
                other_low, other_high = points[:, :2].min(axis=0), points[:, :2].max(axis=0)
                assert np.any(high + 0.06 < other_low) or np.any(other_high + 0.06 < low), (name, low, high, other_low, other_high)
            samples += 1

        for frame in range(45):
            lab.tick(1 / 30)
            check_clearance()
            if frame % 2 == 0:
                capture(animation=True)
        assert display.intro is None and display.values == [2, 0, 0, 1]
        equals_x = [prefix[-1].get_x() for prefix in display.prefixes]
        assert np.ptp(equals_x) < 1e-6, equals_x
        assert not any(isinstance(mob, Text) for mob in scene.get_mobject_family_members())
        prefixes = [prefix.get_all_points().copy() for prefix in display.prefixes]
        capture("initial")
        seen_mutex = set()
        reserved_samples = 0

        def sample():
            nonlocal reserved_samples
            with lab.engine.s.condition:
                snapshot = lab.engine.snapshot()
                expected = [sem.get_value() for sem in (
                    lab.engine.s.empty, lab.engine.s.apples, lab.engine.s.oranges, lab.engine.s.mutex)]
                display.update(snapshot)
                assert display.targets == expected, (snapshot, display.targets, expected)
                seen_mutex.add(expected[-1])
                reserved_samples += any(snapshot["reserved"])
            assert all(np.array_equal(points, prefix.get_all_points())
                       for points, prefix in zip(prefixes, display.prefixes)), "A semaphore prefix moved"
            check_clearance()
            return snapshot

        def drive(predicate, limit=60, render=False):
            deadline = time.monotonic() + limit
            frame = 0
            while time.monotonic() < deadline:
                lab.tick(1 / 30)
                snapshot = sample()
                if render and frame < 150 and frame % 2 == 0:
                    capture(animation=True)
                frame += 1
                if predicate(snapshot):
                    return snapshot
                time.sleep(0.001)
            raise AssertionError((lab.engine.snapshot(), display.values, display.targets))

        def settled():
            return display.intro is None and not display.tracks and display.values == display.targets

        # Display clocks keep advancing during a business pause.
        lab.pause()
        lab.submit("father")
        lab.step()
        drive(lambda s: not lab.stepping, render=True)
        paused_at = lab.business_time
        drive(lambda s: settled(), render=True)
        assert lab.business_time == paused_at
        assert display.values == [1, 1, 0, 1], display.values
        capture("paused_step")
        for _ in range(15):
            capture(animation=True)
        lab.resume()
        drive(lambda s: s["roles"]["father"]["completed"] == 1)

        # Reuse the same prefixes through reset, including an interrupted update.
        lab.demo("concurrent")
        drive(lambda s: not lab.reset_pending and all(info["completed"] == 3 for info in s["roles"].values()))
        drive(lambda s: settled())
        assert lab.presentation.semaphores is display
        assert display.values == [2, 0, 0, 1]
        assert seen_mutex == {0, 1} and reserved_samples > 0
        capture("completed")

        lab.demo("empty")
        drive(lambda s: not lab.reset_pending and s["roles"]["son"]["reason"] == "orange")
        drive(lambda s: "son" in lab.presentation.bubbles and lab.presentation.bubbles["son"].entrance_track.done and settled())
        capture("waiting")
        for key in lab.presentation.actors:
            lab.presentation.waiting(key, "space")
        for _ in range(90):
            lab.tick(1 / 30)
            sample()
        capture("four_clouds")
        if args.render and frames:
            frames[0].save(OUTPUT / "write_and_update.gif", save_all=True, append_images=frames[1:],
                           duration=[60 if i % 3 == 1 else 70 for i in range(len(frames))], loop=0, disposal=2)
        print(f"SEMAPHORES_OK samples={samples}; native four-semaphore values; reservations; mutex 0/1; fixed aligned prefixes; native Write; pause; step; reset reuse; real concurrent completion; actor/fruit/cloud clearance", flush=True)
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
