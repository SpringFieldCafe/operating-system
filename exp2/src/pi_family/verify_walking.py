"""Check real Manim animation geometry, foot contacts, fruit transfers and clocks."""

import numpy as np

from . import FatherPi, MotherPi, SonPi, DaughterPi, WalkTo, carry_fruit, hand_tip, standing_point
from .contact_layout import CONTACT_ROLES, make_contact_pose
from .hand_motion import place_hand, take_hand
from .hand_poses import arm_slice, source_geometry
from .props import AppleOutline
from .reactions import enable_behavior
from .walking import leg_slices
from .verify_contact_fit import _prop_segments, _contour_segment_distance
from .contact_layout import sample_contour


def verify_hands():
    for cls in (FatherPi, MotherPi, SonPi, DaughterPi):
        pi = cls().scale(0.8).shift([0.7, -0.3, 0])
        baseline = pi.body.get_points().copy()
        face = [part.get_all_points().copy() for part in (pi.eyes, pi.mouth)]
        for side in ("left", "right"):
            baseline = pi.body.get_points().copy()
            arm = arm_slice(side)
            fixed = np.ones(len(baseline), dtype=bool)
            fixed[arm] = False
            fixed[arm.start:arm.start+4] = fixed[arm.stop-2:arm.stop] = True
            tips = []
            for mode in (f"{side}_hand_reach", f"{side}_hand_place", "plain"):
                animation = pi.change(mode).build()
                animation.begin()
                for alpha in np.linspace(0, 1, 31):
                    animation.interpolate(float(alpha))
                    assert np.array_equal(pi.body.get_points()[fixed], baseline[fixed])
                    assert all(np.array_equal(part.get_all_points(), data)
                               for part, data in zip((pi.eyes, pi.mouth), face))
                    assert not pi.is_flipped()
                animation.finish()
                tips.append(hand_tip(pi, side))
            assert tips[0][1] > tips[1][1]
            assert np.allclose(pi.body.get_points(), baseline, atol=3e-6)
        pi.change_mode("left_hand_place").change_mode("right_hand_place")
        assert np.allclose(pi.body.get_points()[arm_slice("left")], baseline[arm_slice("left")], atol=3e-6)


def verify_gait():
    for cls in (FatherPi, MotherPi, SonPi, DaughterPi):
        for direction in (-1, 1):
            for held in ("left", "right"):
                pi = cls().scale(0.75).shift([0.3, 0.2, 0])
                start = standing_point(pi).copy()
                fruit = AppleOutline(height=0.25)
                attachment = carry_fruit(pi, fruit, hand=held)
                baseline = pi.body.get_points().copy()
                hand_offset = fruit.get_center() - hand_tip(pi, held)
                animation = WalkTo(pi, start + [direction*2.2, 0, 0], run_time=2.4)
                animation.begin()
                arm = arm_slice(held)
                source, _, _ = source_geometry()
                toes = [leg.start + int(np.argmax(source[leg, 1])) for leg in leg_slices()]
                lifts = [[], []]
                planted = {}
                free_moves = []
                for alpha in np.linspace(0, 1, 241):
                    animation.interpolate(float(alpha))
                    attachment.update()
                    points = pi.body.get_points()
                    assert np.isfinite(pi.get_all_points()).all()
                    assert not pi.is_flipped()
                    assert np.allclose(points[arm], baseline[arm] + animation.applied, atol=4e-6)
                    assert np.allclose(fruit.get_center() - hand_tip(pi, held), hand_offset, atol=4e-6)
                    progress = animation.rate_func(float(alpha))
                    phase = progress*animation.distance/(animation.settings.stride*animation.height)
                    for index, (toe, offset) in enumerate(zip(toes, (0, 0.5))):
                        lift = points[toe, 1] - baseline[toe, 1]
                        lifts[index].append(lift)
                        assert lift > -0.002*animation.height
                        p = (phase + offset) % 1
                        if 0.2 < alpha < 0.8 and 0.08 < p < 0.42:
                            key = (index, int(phase + offset))
                            if key in planted:
                                assert abs(points[toe, 0] - planted[key]) < 0.002*animation.height
                            planted[key] = points[toe, 0]
                    free = arm_slice("right" if held == "left" else "left")
                    free_moves.append(np.max(abs(points[free, 1] - baseline[free, 1] - animation.applied[1])))
                animation.finish()
                assert all(max(values) > 0.025*animation.height for values in lifts)
                assert max(free_moves) > 0.01*animation.height
                assert np.allclose(standing_point(pi), start + [direction*2.2, 0, 0], atol=5e-6)
                assert np.allclose(pi.body.get_points(), baseline + [direction*2.2, 0, 0], atol=5e-6)
                for _ in range(3):
                    back = WalkTo(pi, start, run_time=1)
                    back.begin(); back.interpolate(1); back.finish()
                    forth = WalkTo(pi, start+[direction*2.2, 0, 0], run_time=1)
                    forth.begin(); forth.interpolate(1); forth.finish()
                assert np.allclose(standing_point(pi), start+[direction*2.2, 0, 0], atol=6e-6)
                attachment.release()
                saved = fruit.get_all_points().copy()
                pi.shift([1, 1, 0]); fruit.update(0.1)
                assert np.array_equal(saved, fruit.get_all_points())
        pi = cls()
        still = pi.body.get_points().copy()
        animation = WalkTo(pi, standing_point(pi))
        animation.begin(); animation.interpolate(0.5); animation.finish()
        assert np.allclose(still, pi.body.get_points(), atol=3e-6)


class _MotionScene:
    def __init__(self, fruit, obstacles=None):
        self.time, self.mobjects, self.fruit = 0.0, [], fruit
        self.behavior = None
        self.obstacles = obstacles

    def get_time(self):
        return self.time

    def add(self, obj):
        self.mobjects.append(obj)

    def remove(self, obj):
        self.mobjects.remove(obj)

    def tick(self, dt):
        self.time += dt
        if self.behavior is not None:
            self.behavior.update()
        self.fruit.update(dt)
        if self.obstacles is not None:
            for part in self.fruit.family_members_with_points():
                clearance = _contour_segment_distance(sample_contour(part, 21), self.obstacles)
                assert clearance > 0.012, (getattr(self, "role_key", ""), "carried fruit crossed the table/plate", self.time, clearance)

    def play(self, *animations, run_time=None, rate_func=None):
        animations = [a.build() if hasattr(a, "build") else a for a in animations]
        duration = run_time or max(a.run_time for a in animations)
        for a in animations:
            if rate_func is not None:
                a.rate_func = rate_func
            a.begin()
        steps = max(2, int(duration*30))
        for i in range(1, steps+1):
            for a in animations:
                a.interpolate(i/steps)
            self.tick(duration/steps)
        for a in animations:
            a.finish()
        self.tick(0)

    def wait(self, duration):
        steps = max(2, int(duration*30))
        for _ in range(steps):
            self.tick(duration/steps)


def verify_transfers_and_face():
    for key, role in CONTACT_ROLES.items():
        pi, props = make_contact_pose(key)
        fruit = getattr(props, role.fruit)
        destination = fruit.get_center().copy()
        offset = destination-hand_tip(pi, role.hand)
        pi.change_mode("plain")
        scene = _MotionScene(fruit, _prop_segments(props))
        scene.role_key = key
        scene.behavior = enable_behavior(scene, pi, seed=42)
        controller = scene.behavior.controllers[0]
        next_blink = controller.next_blink
        if key in ("father", "mother"):
            attachment = carry_fruit(pi, fruit, role.hand, offset=offset)
            place_hand(scene, pi, hand=role.hand, fruit=fruit)
            assert not attachment.active
            assert np.allclose(fruit.get_center(), destination, atol=5e-6)
        else:
            take_hand(scene, pi, hand=role.hand, fruit=fruit)
            assert pi._fruit_attachment.active
            assert controller.next_blink == next_blink
            scene.behavior.child_received(pi, role.fruit, mode="hooray")
            try:
                WalkTo(pi, standing_point(pi)+[1,0,0]).begin()
                raise AssertionError("Walking must not overwrite an unfinished celebration.")
            except ValueError:
                pass
            scene.wait(1.95)
        start = standing_point(pi).copy()
        scene.play(WalkTo(pi, start+[role.side*1.5, 0, 0], run_time=4))
        assert len(controller.blink_events) >= 1
        assert controller.blink_events[0] == next_blink
        assert len(controller.gaze_events) >= 1
        assert np.isfinite(pi.get_all_points()).all()
        assert not pi.is_flipped()
        if key not in ("father", "mother"):
            pi._fruit_attachment.update()
            assert scene.behavior.get_state(pi) == "ready"
        scene.behavior.stop()
        attachment = getattr(pi, "_fruit_attachment", None)
        if attachment is not None:
            attachment.release()


def main():
    verify_hands()
    verify_gait()
    verify_transfers_and_face()
    print("Verified both hands on all four roles, unchanged inactive vertices, both travel directions, alternating raised/planted feet, stable held hands, free-arm swings, exact arrival/standing poses, repeated journeys, zero-distance walks, fruit transfers/releases and continuous face clocks.")


if __name__ == "__main__":
    main()
