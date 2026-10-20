"""Verify waiting timing, facial continuity and existing action compatibility."""

import numpy as np

from . import FatherPi, MotherPi, SonPi, DaughterPi, WalkTo, carry_fruit, enable_behavior, hand_tip, standing_point
from .contact_layout import sample_contour
from .expression_geometry import mouth_points
from .face_frame import map_svg_points
from .hand_motion import place_hand, take_hand
from .props import AppleOutline, OrangeOutline
from .verify_idle_motion import _ClockScene
from .verify_reactions import advance
from .verify_walking import _MotionScene


CLASSES = (FatherPi, MotherPi, SonPi, DaughterPi)


def _inside(points, polygon):
    # Independent ray-crossing check against the actual rendered curves.
    x, y = points[:, 0, None], points[:, 1, None]
    a, b = polygon, np.roll(polygon, -1, axis=0)
    crossed = (a[:, 1] > y) != (b[:, 1] > y)
    crossing_x = a[:, 0]+(y-a[:, 1])*(b[:, 0]-a[:, 0])/(b[:, 1]-a[:, 1]+1e-20)
    return np.sum(crossed & (x < crossing_x), axis=1) % 2 == 1


def _check_open_face(pi):
    for eye in pi.eyes:
        iris = sample_contour(eye.iris, 12)[:, :2]
        pupil = sample_contour(eye.pupil[0], 12)[:, :2]
        assert _inside(pupil, iris).all(), (type(pi).__name__, "pupil left the angry eye")
    if hasattr(pi, "eyelashes"):
        assert len(pi.eyelashes) == 6
        for index, eye in enumerate(pi.eyes):
            contour = sample_contour(eye.iris, 25)
            for lash in pi.eyelashes[index*3:index*3+3]:
                gap = np.linalg.norm(contour-lash.get_points()[0], axis=1).min()
                assert gap < 0.03*eye.iris.get_width(), (type(pi).__name__, "lash detached", gap)


def verify_all_faces():
    for cls in CLASSES:
        for rest in ("plain", "left_hand_hold", "right_hand_hold"):
            pi = cls(mode=rest).scale(0.8).shift([0.4, -0.2, 0])
            body = pi.body.get_points().copy()
            original = [eye.iris.get_points().copy() for eye in pi.eyes]
            widths = [eye.iris.get_width() for eye in pi.eyes]
            pupil_widths = [eye.pupil.get_width() for eye in pi.eyes]
            scene = _ClockScene()
            motion = enable_behavior(scene, pi, seed=12)
            idle, actor = motion.controllers[0], motion.reactions[0]
            advance(scene, motion, 0.5, fps=24)
            motion.waiting(pi)
            advance(scene, motion, 1.4, fps=24)
            motion.waiting(pi)
            assert actor.waiting_started == 0.5
            advance(scene, motion, 2.499, fps=24)
            assert motion.get_expression(pi) == "waiting" and idle.anger == 0
            assert all(np.allclose(eye.iris.get_points(), points, atol=2e-6) for eye, points in zip(pi.eyes, original))
            scene.time = 2.5
            motion.update()
            assert motion.get_expression(pi) == "angry" and idle.anger == 0
            pupils = [eye.pupil.get_center().copy() for eye in pi.eyes]
            scene.time += 1e-6
            motion.update()
            assert all(np.linalg.norm(eye.pupil.get_center()-point) < 2e-5*eye.iris.get_width()
                       for eye, point in zip(pi.eyes, pupils)), "Pupils jumped at anger onset."
            advance(scene, motion, 2.7, fps=24)
            assert abs(idle.anger-0.5) < 1e-8
            advance(scene, motion, 2.9, fps=24)
            assert abs(idle.anger-1) < 1e-8
            assert motion.get_state(pi) == "waiting"
            assert np.allclose(pi.mouth.get_points(), map_svg_points(mouth_points("angry"), pi), atol=2e-6)
            _check_open_face(pi)
            for eye, width, pupil_width in zip(pi.eyes, widths, pupil_widths):
                assert abs(eye.iris.get_width()/width-1) < 0.005
                assert abs(eye.pupil.get_width()-pupil_width) < 2e-6
            events = list(actor.events)
            motion.waiting(pi)
            motion.update()
            assert actor.events == events
            for time in np.linspace(2.9, 6.1, 97):
                scene.time = float(time)
                motion.update()
                assert np.array_equal(pi.body.get_points(), body)
                assert pi.get_mode() == rest and not pi._body_reaction_active
                assert np.isfinite(pi.get_all_points()).all()
                if time > idle.blink_started+idle.settings.blink_duration:
                    _check_open_face(pi)
            # Recovery begins from the visible face, without an instant jump.
            parts = [pi.eyes, pi.mouth]+([pi.eyelashes] if hasattr(pi, "eyelashes") else [])
            snapshots = [part.get_all_points().copy() for part in parts]
            motion.ready(pi)
            motion.update()
            assert all(np.allclose(part.get_all_points(), data, atol=2e-6) for part, data in zip(parts, snapshots))
            advance(scene, motion, 6.6, fps=24)
            idle.update(scene.time, blink=False)
            assert idle.anger == 0
            assert all(np.allclose(eye.iris.get_points(), points, atol=2e-6) for eye, points in zip(pi.eyes, original))
            baseline_scene = _ClockScene()
            baseline = enable_behavior(baseline_scene, cls(mode=rest), seed=12)
            baseline_scene.time = 6.6
            baseline.update()
            assert idle.blink_events == baseline.controllers[0].blink_events
            baseline.stop()
            motion.stop()
            assert np.array_equal(pi.body.get_points(), body)


def verify_short_waits_and_interruptions():
    for cls in CLASSES:
        pi = cls().flip().scale(0.7)
        scene = _ClockScene()
        motion = enable_behavior(scene, pi, seed=2)
        idle = motion.controllers[0]
        # An ordinary pause never creates a waiting state.
        advance(scene, motion, 3, fps=24)
        assert idle.anger == 0 and motion.get_state(pi) == "ready"
        motion.waiting(pi)
        advance(scene, motion, 4.8, fps=24)
        motion.ready(pi)
        advance(scene, motion, 6, fps=24)
        assert not any(e[1] == "impatient" for e in motion.reactions[0].events)
        motion.waiting(pi)
        advance(scene, motion, 8.2, fps=24)
        assert abs(idle.anger-0.5) < 1e-8
        parts = (pi.eyes, pi.mouth)
        snapshots = [part.get_all_points().copy() for part in parts]
        motion.ready(pi)
        motion.update()
        assert all(np.allclose(part.get_all_points(), data, atol=2e-6) for part, data in zip(parts, snapshots))
        advance(scene, motion, 8.7, fps=24)
        assert idle.anger == 0
        # Re-entering waiting starts a fresh 2-second interval.
        motion.waiting(pi)
        advance(scene, motion, 10.69, fps=24)
        assert idle.anger == 0
        advance(scene, motion, 11.2, fps=24)
        assert idle.anger == 1
        motion.stop()
        assert idle.anger == 0 and not scene.mobjects


def verify_action_compatibility():
    for cls in CLASSES:
        for hand in ("left", "right"):
            pi = cls()
            fruit = OrangeOutline() if cls in (MotherPi, SonPi) else AppleOutline()
            scene = _MotionScene(fruit)
            attachment = carry_fruit(pi, fruit, hand=hand)
            scene.behavior = enable_behavior(scene, pi, seed=12)
            scene.behavior.waiting(pi)
            scene.wait(2.5)
            assert scene.behavior.get_expression(pi) == "angry"
            offset = fruit.get_center()-hand_tip(pi, hand)
            start = standing_point(pi).copy()
            scene.play(WalkTo(pi, start+[1, 0, 0], run_time=0.8))
            assert attachment.active and np.allclose(fruit.get_center()-hand_tip(pi, hand), offset, atol=2e-6)
            # Both existing hand helpers must preserve the composed eyes.
            place_hand(scene, pi, hand=hand, fruit=fruit, run_time=0.6)
            assert not attachment.active
            take_hand(scene, pi, hand=hand, fruit=fruit, run_time=0.6)
            assert pi._fruit_attachment.active
            scene.behavior.ready(pi)
            scene.wait(0.5)
            assert scene.behavior.controllers[0].anger == 0
            scene.behavior.stop()
            pi._fruit_attachment.release()


def main():
    verify_all_faces()
    verify_short_waits_and_interruptions()
    verify_action_compatibility()
    print("Verified four angry faces, 2s/0.4s timing, unchanged standing/held body poses, pupils within eyes, attached lashes, continuous recovery, repeated/short waits, mirroring, unchanged blink clocks, both hands, held fruit and walking compatibility.")


if __name__ == "__main__":
    main()
