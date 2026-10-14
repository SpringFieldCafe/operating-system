"""Check independent timing, face-only updates, and compatibility with the hand."""

import numpy as np

from .creatures import DaughterPi, FatherPi, MotherPi, SonPi
from .idle_motion import CreatureIdle, IdleSettings, enable_idle


class _ClockScene:
    def __init__(self):
        self.time = 0.0
        self.mobjects = []

    def get_time(self):
        return self.time

    def add(self, mobject):
        self.mobjects.append(mobject)

    def remove(self, mobject):
        self.mobjects.remove(mobject)


def verify_timelines():
    timelines = []
    settings = IdleSettings()
    for role_index, cls in enumerate((FatherPi, MotherPi, SonPi, DaughterPi)):
        pi = cls()
        body, mouth = pi.body.get_points().copy(), pi.mouth.get_all_points().copy()
        controller = CreatureIdle(pi, 100 + role_index, settings)
        for time in np.linspace(0, 60, 1801):
            controller.update(float(time))
            assert np.array_equal(pi.body.get_points(), body)
            assert np.array_equal(pi.mouth.get_all_points(), mouth)
            assert np.isfinite(pi.get_all_points()).all()
        intervals = np.diff([0, *controller.blink_events])
        assert np.all((intervals >= 3) & (intervals <= 5))
        assert {event[1] for event in controller.gaze_events} == {0, 1, 2}
        assert 12 <= len(controller.blink_events) <= 20
        timelines.append(tuple(controller.blink_events))

        # A single large clock step must select the same events and final pose
        # as a full minute of small frame steps, for reproducible report renders.
        replay = CreatureIdle(cls(), 100 + role_index, settings)
        replay.update(60)
        assert replay.blink_events == controller.blink_events
        assert replay.gaze_events == controller.gaze_events
        assert np.allclose(replay.pi.eyes.get_all_points(), pi.eyes.get_all_points(), atol=2e-6)
    assert len(set(timelines)) == 4


def verify_blink_and_hand():
    for cls in (FatherPi, MotherPi, SonPi, DaughterPi):
        for flipped in (False, True):
            pi = cls()
            if flipped:
                pi.flip()
            pi.scale(0.8)
            baseline = pi.copy()
            scene = _ClockScene()
            idle = enable_idle(scene, pi, seed=7)
            controller = idle.controllers[0]
            scene.time = controller.next_blink + 0.5 * controller.settings.blink_duration
            idle.update()
            assert pi.eyes.get_height() < 1e-5
            if hasattr(pi, "eyelashes"):
                assert pi.eyelashes.get_height() < 1e-5

            actual = pi.copy().change_mode("left_hand_reach")
            expected = baseline.copy().change_mode("left_hand_reach")
            assert np.allclose(actual.body.get_points(), expected.body.get_points(), atol=3e-6)

            # Let the same clock advance while the stored placement pose runs.
            animation = pi.change("left_hand_place").build()
            animation.begin()
            before = len(controller.blink_events)
            for alpha in np.linspace(0, 1, 61):
                animation.interpolate(float(alpha))
                scene.time += 0.1
                idle.update()
                assert np.isfinite(pi.get_all_points()).all()
            animation.finish()
            idle.update()
            assert len(controller.blink_events) > before
            idle.stop()
            assert not hasattr(pi, "_ambient_face_active")
            assert pi.eyes.get_height() > 0
            assert not scene.mobjects


def main():
    verify_timelines()
    verify_blink_and_hand()
    print("Verified independent 3-5 second blink intervals, three scan versions per role, seeded clock replay, face-only updates, mirrored blinks, and continuous timing during the saved hand gesture.")


if __name__ == "__main__":
    main()
