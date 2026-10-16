"""Render and exercise the actual scene without the interactive prompt."""

import argparse
from pathlib import Path
import time
import sys

OUTPUT = Path(__file__).resolve().parents[1] / "pi_family" / "preview"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial-only", action="store_true")
    args = parser.parse_args()
    # ManimGL parses argv at import time. Keep verification flags out of it.
    sys.argv[:] = [sys.argv[0]]
    from .scene import FruitLabScene
    scene = FruitLabScene(camera_config={"fps": 30})
    try:
        print("BUILDING_SCENE", flush=True)
        scene.build_lab()
        print("SCENE_BUILT", flush=True)
        scene.update_frame(1 / 30, force_draw=True)
        OUTPUT.mkdir(exist_ok=True)
        scene.get_image().save(OUTPUT / "lab_initial.png")
        if args.initial_only:
            return
        lab = scene.lab
        lab.detail(True)
        lab.batch(father=2, mother=2, son=2, daughter=2)
        markers = set()
        deadline = time.monotonic() + 90
        frames = 0
        while time.monotonic() < deadline:
            scene.update_frame(1 / 30, force_draw=True)
            frames += 1
            view = lab.presentation
            labels = {"lab_waiting": bool(view.bubbles) and lab.business_time > 1.2,
                      "lab_angry": any(c.anger > 0.99 for c in view.behavior.controllers),
                      "lab_contact": any(p == "contact" for p in view.phases.values()),
                      "lab_celebrating": any(a.celebration and lab.business_time - a.celebration[0] > 0.6 for a in view.behavior.reactions),
                      "lab_overlap": sum(p in ("outbound", "returning") for p in view.phases.values()) >= 2}
            for name, ready in labels.items():
                if ready and name not in markers:
                    scene.get_image().save(OUTPUT / (name + ".png"))
                    markers.add(name)
            snapshot = lab.engine.snapshot()
            if all(v["completed"] == 2 for v in snapshot["roles"].values()) and not view.tracks:
                break
        else:
            raise AssertionError(f"Visual workload timed out: {lab.engine.snapshot()}, {lab.presentation.phases}")
        assert snapshot["slots"] == [None, None]
        assert "lab_overlap" in markers, markers
        lab.pause()
        positions = {k: p.body.get_points().copy() for k, p in view.actors.items()}
        clocks = [len(c.blink_events) for c in view.behavior.controllers]
        for _ in range(180):
            scene.update_frame(1 / 30, force_draw=True)
        import numpy as np
        assert all(np.array_equal(positions[k], p.body.get_points()) for k, p in view.actors.items())
        assert any(len(c.blink_events) > n for c, n in zip(view.behavior.controllers, clocks))
        scene.get_image().save(OUTPUT / "lab_completed.png")
        print(f"VISUAL_CHECKS_OK frames={frames} markers={sorted(markers)}", flush=True)
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
