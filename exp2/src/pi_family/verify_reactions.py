"""Check event rules and continuity at gaze, blink, and pose handoffs."""

import numpy as np

from .creatures import FatherPi, MotherPi, SonPi, DaughterPi, make_family
from .hand_poses import source_geometry
from .idle_motion import enable_idle
from .reactions import enable_behavior
from .verify_idle_motion import _ClockScene


def advance(scene, motion, end, fps=60):
    start = scene.time
    count = max(1, round((end - start) * fps))
    for time in np.linspace(start, end, count + 1):
        scene.time = float(time)
        motion.update()


def verify_parent_and_waiting():
    for cls in (FatherPi, MotherPi, SonPi, DaughterPi):
        for flipped in (False, True):
            pi = cls()
            if flipped:
                pi.flip()
            pi.scale(0.8)
            body = pi.body.get_points().copy()
            scene = _ClockScene()
            motion = enable_behavior(scene, pi, seed=2)
            actor = motion.reactions[0]
            iris = [eye.iris.get_points().copy() for eye in pi.eyes]
            width = [eye.iris.get_width() for eye in pi.eyes]
            advance(scene, motion, 1)
            before = actor.random.getstate()
            events = list(actor.events)
            motion.ready(pi)
            assert actor.random.getstate() == before and actor.events == events
            motion.waiting(pi)
            advance(scene, motion, 1.5)
            mouth = pi.mouth.get_points().copy()
            motion.waiting(pi)
            motion.update()
            assert np.array_equal(pi.mouth.get_points(), mouth)
            motion.ready(pi)
            advance(scene, motion, 2)
            assert np.array_equal(pi.body.get_points(), body)
            for eye, points, original_width in zip(pi.eyes, iris, width):
                assert np.allclose(eye.iris.get_points(), points, atol=1e-7)
                assert abs(eye.iris.get_width() - original_width) < 1e-7
            if actor.is_parent:
                choices = [motion.parent_placed(pi) for _ in range(1000)]
                assert set(choices) == {"plain", "parent_smile"}
                assert 450 < choices.count("parent_smile") < 550
            motion.stop()
            assert not scene.mobjects


def verify_gaze_and_blink_handoffs():
    raw, _, _ = source_geometry()
    legs = raw[:, 1] > 215
    right_tip = int(np.argmin(np.linalg.norm(raw - [395.9, 139, 0], axis=1)))
    left_tip = int(np.argmin(np.linalg.norm(raw - [95.7, 204.5, 0], axis=1)))
    for cls, fruit in ((SonPi, "orange"), (DaughterPi, "apple")):
        for flipped in (False, True):
            for trigger in ("mid_scan", "mid_blink"):
                for mode in ("happy", "hooray"):
                    pi = cls()
                    if flipped:
                        pi.flip()
                    pi.scale(0.85)
                    scene = _ClockScene()
                    motion = enable_behavior(scene, pi, seed=17)
                    idle = motion.controllers[0]
                    if trigger == "mid_scan":
                        advance(scene, motion, idle.next_gaze)
                        advance(scene, motion, scene.time + 0.5 * idle.gaze_duration)
                    else:
                        advance(scene, motion, idle.next_blink + 0.5 * idle.settings.blink_duration)
                        assert pi.eyes.get_height() < 1e-5
                    body = pi.body.get_points().copy()
                    eyes = pi.eyes.get_all_points().copy()
                    lashes = pi.eyelashes.get_all_points().copy() if hasattr(pi, "eyelashes") else None
                    next_blink, blink_events = idle.next_blink, list(idle.blink_events)
                    motion.child_received(pi, fruit, mode=mode)
                    motion.update()
                    assert np.allclose(pi.eyes.get_all_points(), eyes, atol=1e-7)
                    if lashes is not None:
                        assert np.allclose(pi.eyelashes.get_all_points(), lashes, atol=1e-7)
                    assert idle.next_blink == next_blink and idle.blink_events == blink_events
                    started = scene.time
                    previous = idle.face.eyes[0].pupil.get_center().copy()
                    maximum_step = 0.0
                    peak = None
                    for time in np.linspace(started, started + 3, 181):
                        scene.time = float(time)
                        motion.update()
                        current = idle.face.eyes[0].pupil.get_center()
                        maximum_step = max(maximum_step, np.linalg.norm(current - previous))
                        previous = current.copy()
                        assert np.array_equal(pi.body.get_points()[legs], body[legs])
                        if mode == "happy":
                            assert np.array_equal(pi.body.get_points(), body)
                        if 0.5 < time - started < 0.8:
                            peak = pi.body.get_points().copy()
                        assert np.isfinite(pi.get_all_points()).all()
                    assert maximum_step < 0.2 * idle.face.eyes[0].iris.get_width()
                    if mode == "hooray":
                        assert peak[left_tip, 1] - body[left_tip, 1] > 0.2 * pi.body.get_height()
                        assert peak[right_tip, 1] - body[right_tip, 1] > 0.02 * pi.body.get_height()
                    assert motion.get_state(pi) == "ready"
                    assert motion.get_expression(pi) == "plain"
                    assert idle.focus_target is None
                    assert np.allclose(pi.body.get_points(), body, atol=2e-6)
                    motion.stop()


def verify_independent_rules():
    family = make_family()
    scene = _ClockScene()
    motion = enable_behavior(scene, family, seed=2)
    plain_scene = _ClockScene()
    original = enable_idle(plain_scene, make_family(), seed=2)
    children = motion.reactions[2:]
    for actor in children:
        state = actor.random.getstate()
        try:
            motion.child_received(actor.pi, "apple" if actor.fruit == "orange" else "orange")
        except ValueError:
            pass
        else:
            raise AssertionError("Wrong fruit must not trigger a celebration.")
        assert actor.random.getstate() == state
        assert actor.state == "ready"
    for round_index in range(2):
        for actor in children:
            motion.child_received(actor.pi, actor.fruit)
            advance(scene, motion, scene.time + 2)
    for actor in children:
        assert {event[2] for event in actor.events if event[1] == "received"} == {"happy", "hooray"}
    advance(scene, motion, 20)
    advance(plain_scene, original, 20)
    for idle, baseline in zip(motion.controllers, original.controllers):
        assert idle.blink_events == baseline.blink_events
    assert len({tuple(idle.blink_events) for idle in motion.controllers}) == 4
    motion.stop()
    original.stop()

    # Stopping the behavior layer must not reset a hand gesture it does not own.
    pi = SonPi()
    scene = _ClockScene()
    motion = enable_behavior(scene, pi, seed=2)
    pi.change_mode("left_hand_reach")
    body = pi.body.get_points().copy()
    motion.stop()
    assert np.array_equal(pi.body.get_points(), body)


def verify_waiting_interrupt():
    pi = DaughterPi()
    pi.flip()
    scene = _ClockScene()
    motion = enable_behavior(scene, pi, seed=2)
    body = pi.body.get_points().copy()
    motion.child_received(pi, "apple", mode="hooray")
    advance(scene, motion, 0.23)
    parts = (pi.body, pi.mouth, pi.eyes, pi.eyelashes)
    snapshots = [part.get_all_points().copy() for part in parts]
    motion.waiting(pi)
    motion.update()
    for part, before in zip(parts, snapshots):
        assert np.allclose(part.get_all_points(), before, atol=1e-7)
    advance(scene, motion, 0.8)
    assert motion.get_state(pi) == "waiting"
    assert np.allclose(pi.body.get_points(), body, atol=2e-6)
    motion.ready(pi)
    motion.child_received(pi, "apple", mode="happy")
    advance(scene, motion, 2.9)
    assert motion.get_state(pi) == "ready"
    motion.stop()


def main():
    verify_parent_and_waiting()
    verify_gaze_and_blink_handoffs()
    verify_independent_rules()
    verify_waiting_interrupt()
    print("Verified parent 50/50 round sampling, idempotent state changes, correct child fruit rules, both child poses, mid-scan/mid-blink handoffs, mirrored/scaled continuity, stationary legs, gaze resume, unchanged independent blink clocks, continuous interruption into waiting, and clean shutdown.")


if __name__ == "__main__":
    main()
