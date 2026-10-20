"""Sample real process-driven fruit geometry, ownership, and refill timing."""

from pathlib import Path
import sys
import time


def main():
    render = "--render" in sys.argv
    sys.argv[:] = [sys.argv[0]]
    import numpy as np
    from manimlib import Scene
    from pi_family.contact_layout import CONTACT_ROLES
    from pi_family.props import AppleOutline
    from .scene import FruitLabScene
    from .visuals import Clip

    output = Path(__file__).resolve().parents[3] / ".privacy-review" / "fruit-timing" / "after"
    output.mkdir(parents=True, exist_ok=True)
    scene = FruitLabScene(camera_config={"resolution": (1280, 720), "fps": 60})
    case = "startup"
    samples, slides, frames = 0, [], []
    grants, slide_keys = {}, set()
    captured, active_slides = set(), set()

    def fruit_kind(fruit):
        return "apple" if isinstance(fruit, AppleOutline) else "orange"

    def bounds(fruit):
        points = fruit.get_all_points()[:, :2]
        return points.min(axis=0), points.max(axis=0)

    def overlap(a, b):
        low_a, high_a = bounds(a)
        low_b, high_b = bounds(b)
        return bool(np.all(np.minimum(high_a, high_b) - np.maximum(low_a, low_b) > 0.003))

    def hook():
        view = scene.lab.presentation
        original = view.on_event

        def on_event(event):
            if event["kind"] == "granted":
                grants[event["role"]] = dict(event=event,
                    pictures={id(fruit): fruit.get_bottom().copy() for fruit in view.plate_fruits.values()})
                assert not active_slides, (case, "new grant during unfinished slide")
            original(event)

        view.on_event = on_event

    def audit():
        nonlocal samples
        lab, view = scene.lab, scene.lab.presentation
        snapshot = lab.engine.snapshot()
        samples += 1
        plate = list(view.plate_fruits.values())
        assert len(plate) <= 2 and len({id(fruit) for fruit in plate}) == len(plate)
        assert not ({id(fruit) for fruit in plate} & {id(fruit) for fruit in view.carried.values()})
        for fruit in plate:
            assert abs(bounds(fruit)[0][1] - view.positions[0][1]) < 0.002, (case, "fruit below plate")
            assert not getattr(fruit, "_hand_attachment", None)
        if len(plate) == 2:
            assert not overlap(*plate), (case, "two plate fruits cross")
        for fruit in plate:
            for carried in view.carried.values():
                assert not overlap(fruit, carried), (case, "plate and carried fruit intersect")
        current_slides = set()
        for key, track in view.tracks.items():
            phase = view.phases[key]
            child = key in ("son", "daughter")
            grant = grants[key]
            if child and phase in ("outbound", "contact"):
                # No fruit may move while the child approaches or withdraws.
                for fruit in plate:
                    assert np.allclose(fruit.get_bottom(), grant["pictures"][id(fruit)], atol=1e-5), (case, "premature slide")
                if key not in view.carried:
                    selected = view.plate_fruits[grant["event"]["slot"]]
                    near = 1 if CONTACT_ROLES[key].side > 0 else 0
                    assert fruit_kind(selected) == grant["event"]["fruit"]
                    assert np.allclose(selected.get_bottom(), view.positions[near], atol=1e-5), (case, "wrong-side take")
            if phase == "arranging" and isinstance(track.current, Clip):
                identity = (lab.epoch, grant["event"]["task"])
                current_slides.add(identity)
                assert snapshot["owner"] == key, (case, "slide without ownership")
                assert abs(track.current.duration - 0.45) < 1e-10
                assert view.actors[key].get_mode().endswith("_hand_hold"), (case, "slide before hand withdrawal")
                if identity not in slide_keys:
                    slide_keys.add(identity)
                    slides.append((case, key, lab.business_time))
                    if render and child:
                        Scene.update_frame(scene, 0, force_draw=True)
                        scene.get_image().save(output / (case + "_refill_start.png"))
            marker = (case, key, phase)
            if render and child and marker not in captured and phase in ("outbound", "contact", "returning"):
                captured.add(marker)
                Scene.update_frame(scene, 0, force_draw=True)
                scene.get_image().save(output / (case + "_" + key + "_" + phase + ".png"))
        active_slides.clear()
        active_slides.update(current_slides)
        if render and case == "two_apples" and view.phases["daughter"] in ("contact", "arranging", "returning"):
            if samples % 2 == 0 and len(frames) < 180:
                Scene.update_frame(scene, 0, force_draw=True)
                frames.append(scene.get_image().convert("RGB").resize((960, 540)))

    def pump(dt=1 / 60):
        scene.lab.tick(dt)
        audit()
        time.sleep(0.001)  # Yield to real workers; this does not select a winner.

    def drive(predicate, limit=90):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            pump()
            if predicate(scene.lab.engine.snapshot()):
                return
        raise AssertionError((case, "timeout", scene.lab.engine.snapshot(), scene.lab.presentation.phases))

    def done(snapshot, **counts):
        return not scene.lab.presentation.tracks and all(snapshot["roles"][key]["completed"] == count for key, count in counts.items())

    def run(**counts):
        snapshot = scene.lab.engine.snapshot()
        expected = {key: snapshot["roles"][key]["completed"] + count for key, count in counts.items()}
        scene.lab.batch(**counts)
        drive(lambda state: done(state, **expected))

    def fresh(name, rate=1):
        nonlocal case
        scene.lab.reset()
        # Reset replaces the view. No work is submitted until its hook is set.
        deadline = time.monotonic() + 90
        while scene.lab.reset_pending:
            if time.monotonic() > deadline:
                raise AssertionError("reset timed out")
            scene.lab.tick(1 / 60)
            time.sleep(0.001)
        grants.clear()
        active_slides.clear()
        case = name
        hook()
        scene.lab.speed(rate)

    def canonical():
        view = scene.lab.presentation
        for fruit in view.plate_fruits.values():
            side = 1 if fruit_kind(fruit) == "apple" else 0
            assert np.allclose(fruit.get_bottom(), view.positions[side], atol=1e-5), (case, "wrong refill side")

    def passed():
        print("FRUIT_CASE_OK", case, flush=True)

    try:
        scene.build_lab()
        hook()
        for producer, consumer, name in (("father", "daughter", "two_apples"), ("mother", "son", "two_oranges")):
            fresh(name)
            run(**{producer: 2})
            start = len(slides)
            run(**{consumer: 2})
            assert [entry[1] for entry in slides[start:]] == [consumer]
            assert not scene.lab.presentation.plate_fruits
            passed()

        for first, second, consumers, name in (
            ("father", "mother", ("daughter", "son"), "mixed_father_first"),
            ("mother", "father", ("son", "daughter"), "mixed_mother_first"),
        ):
            fresh(name)
            run(**{first: 1})
            run(**{second: 1})
            canonical()
            start = len(slides)
            for consumer in consumers:
                run(**{consumer: 1})
                canonical()
            assert len(slides) == start, (case, "mixed fruit moved unnecessarily")
            passed()

        fresh("refill_then_other_parent")
        run(father=2)
        run(daughter=1)
        canonical()
        run(mother=1)
        canonical()
        run(son=1, daughter=1)
        passed()

        fresh("orange_refill_then_father")
        run(mother=2)
        run(son=1)
        canonical()
        run(father=1)
        canonical()
        run(son=1, daughter=1)
        passed()

        fresh("pause_and_step_during_refill")
        run(father=2)
        scene.lab.batch(daughter=1, mother=1)
        drive(lambda state: scene.lab.presentation.phases["daughter"] == "arranging")
        scene.lab.pause()
        frozen = {id(fruit): fruit.get_all_points().copy() for fruit in scene.lab.presentation.plate_fruits.values()}
        before = scene.lab.business_time
        for _ in range(20):
            pump(0.05)
        assert scene.lab.business_time == before
        assert all(np.array_equal(fruit.get_all_points(), frozen[id(fruit)]) for fruit in scene.lab.presentation.plate_fruits.values())
        scene.lab.step()
        drive(lambda state: not scene.lab.stepping)
        assert scene.lab.paused and scene.lab.engine.snapshot()["owner"] is None
        canonical()
        scene.lab.resume()
        drive(lambda state: done(state, daughter=1, mother=1))
        passed()

        fresh("speed_change_during_refill")
        run(mother=2)
        scene.lab.submit("son", 1)
        drive(lambda state: scene.lab.presentation.phases["son"] == "arranging")
        scene.lab.speed(0.25)
        for _ in range(4):
            pump()
        scene.lab.speed(4)
        drive(lambda state: done(state, son=1))
        canonical()
        passed()

        fresh("reset_during_refill")
        run(father=2)
        scene.lab.submit("daughter", 1)
        drive(lambda state: scene.lab.presentation.phases["daughter"] == "arranging")
        scene.lab.reset()
        # Audit the old view while its already-started trip finishes.
        deadline = time.monotonic() + 90
        while scene.lab.reset_pending:
            if time.monotonic() > deadline:
                raise AssertionError((case, "reset timed out"))
            scene.lab.tick(1 / 60)
            if scene.lab.reset_pending:
                audit()
            time.sleep(0.001)
        hook()
        grants.clear()
        active_slides.clear()
        assert not scene.lab.presentation.plate_fruits
        run(father=1, daughter=1)
        passed()

        fresh("four_role_competition", rate=4)
        run(father=3, mother=3, son=3, daughter=3)
        assert scene.lab.engine.snapshot()["slots"] == [None, None]
        assert len({info["pid"] for info in scene.lab.engine.snapshot()["roles"].values()}) == 4
        passed()
        if frames:
            from PIL import Image
            atlas = Image.new("RGB", (240, 135 * len(frames[::8])))
            for index, frame in enumerate(frames[::8]):
                atlas.paste(frame.resize((240, 135)), (0, 135 * index))
            palette = atlas.quantize(colors=256)
            indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
            indexed[0].save(output / "fruit_refill.gif", save_all=True, append_images=indexed[1:],
                            duration=[30 if i % 3 != 1 else 40 for i in range(len(indexed))],
                            loop=0, disposal=2, optimize=False)
        print(f"FRUIT_TIMING_OK cases=10 samples={samples} slides={len(slides)}", flush=True)
    except BaseException:
        if hasattr(scene, "lab"):
            Scene.update_frame(scene, 0, force_draw=True)
            scene.get_image().save(output / (case + "_failure.png"))
        raise
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
