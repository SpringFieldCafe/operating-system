"""Event-driven family expressions, with the author's gaze/blink algorithms."""

from dataclasses import dataclass
import random

import numpy as np
from manimlib import VMobject, smooth

from .expression_geometry import celebration_body_points, mouth_points
from .face_frame import map_svg_points
from .hand_poses import source_geometry
from .idle_motion import IdleMotion, _mark_face_dynamic


@dataclass(frozen=True)
class ReactionSettings:
    mouth_duration: float = 0.3
    gaze_duration: float = 0.35
    celebration_enter: float = 0.45
    celebration_hold: float = 0.9
    celebration_exit: float = 0.45

    def __post_init__(self):
        if any(value <= 0 for value in vars(self).values()):
            raise ValueError("Reaction durations must be positive.")

    @property
    def celebration_duration(self):
        return self.celebration_enter + self.celebration_hold + self.celebration_exit


def left_hand_focus(pi):
    """A live hand attachment point; a future fruit Mobject may be used instead."""
    body, _, arm = source_geometry()
    tip = arm.start + int(np.argmin(body[arm, 0]))
    return pi.body.get_points()[tip].copy()


def _interpolate_shape(shape, start, end, alpha):
    # Native Manim vector interpolation; preserve equal vertices exactly.
    shape.interpolate(start, end, smooth(np.clip(alpha, 0, 1)))
    fixed = np.all(start.get_points() == end.get_points(), axis=1)
    if fixed.any():
        points = shape.get_points().copy()
        points[fixed] = start.get_points()[fixed]
        shape.set_points(points)


def _shape(points):
    return VMobject().set_points(points.copy())


class CreatureReaction:
    """One actor's explicit lab state; presentation never decides lab order."""

    def __init__(self, pi, idle, seed, settings):
        self.pi, self.idle, self.settings = pi, idle, settings
        self.random = random.Random(seed)
        self.is_parent = type(pi).__name__ in ("FatherPi", "MotherPi")
        self.fruit = {"SonPi": "orange", "DaughterPi": "apple"}.get(type(pi).__name__)
        self.state = "initial" if self.is_parent else "ready"
        self.expression = "plain"
        self.mouth = _shape(mouth_points("plain"))
        self.mouth_start = self.mouth.copy()
        self.mouth_goal = self.mouth.copy()
        self.mouth_started = -float("inf")
        self.body = _shape(celebration_body_points("plain"))
        self.body_start = self.body.copy()
        self.body_goal = self.body.copy()
        self.celebration = None
        self.body_return = None
        self.events = []
        if self.is_parent:
            self.ready(0)

    def _mouth_at(self, time):
        alpha = (time - self.mouth_started) / self.settings.mouth_duration
        _interpolate_shape(self.mouth, self.mouth_start, self.mouth_goal, alpha)

    def _set_mouth(self, expression, time):
        self._mouth_at(time)
        self.mouth_start = self.mouth.copy()
        self.mouth_goal = _shape(mouth_points(expression))
        self.mouth_started = time
        self.expression = expression

    def _cancel_celebration(self, time):
        if self.celebration is not None:
            self._body_at(time)
            self.body_return = (time, self.body.copy())
            self.celebration = None
            self.idle.release_focus(time)

    def ready(self, time, new_round=False):
        if self.state == "ready" and not new_round:
            return self.expression
        self._cancel_celebration(time)
        self.state = "ready"
        mode = self.random.choice(("plain", "parent_smile")) if self.is_parent else "plain"
        self._set_mouth(mode, time)
        self.events.append((time, "ready", mode))
        return mode

    def waiting(self, time):
        if self.state == "waiting":
            return
        self._cancel_celebration(time)
        self.state = "waiting"
        self._set_mouth("waiting", time)
        self.events.append((time, "waiting", "waiting"))

    def received(self, fruit, time, look_target=None, mode=None):
        fruit = {"苹果": "apple", "橘子": "orange", "桔子": "orange"}.get(fruit, fruit)
        if self.is_parent or fruit != self.fruit:
            raise ValueError("Son receives orange; Daughter receives apple; parents do not celebrate taking fruit.")
        if self.pi.get_mode() != "plain" or self.celebration is not None or self.body_return is not None:
            raise ValueError("Finish the take/return gesture before starting a celebration.")
        if mode is not None and mode not in ("happy", "hooray"):
            raise ValueError("Choose happy or hooray, or omit mode for independent 50/50 sampling.")
        mode = self.random.choice(("happy", "hooray")) if mode is None else mode
        # Load/validate before taking ownership of the actor's state.
        body = celebration_body_points(mode)
        mouth_points(mode)
        self.state = "celebrating"
        self.celebration = (time, mode)
        self.body_start = _shape(celebration_body_points("plain"))
        self.body_goal = _shape(body)
        self._set_mouth(mode, time)
        self.idle.focus_on(look_target if look_target is not None else lambda: left_hand_focus(self.pi), time, self.settings.gaze_duration)
        self.events.append((time, "received", mode))
        return mode

    def _body_at(self, time):
        if self.body_return is not None:
            started, start = self.body_return
            alpha = (time - started) / self.settings.celebration_exit
            _interpolate_shape(self.body, start, _shape(celebration_body_points("plain")), alpha)
            if alpha >= 1:
                self.body_return = None
            return True
        if self.celebration is None:
            return False
        started, _ = self.celebration
        elapsed = time - started
        hold_ends = self.settings.celebration_enter + self.settings.celebration_hold
        if elapsed <= self.settings.celebration_enter:
            _interpolate_shape(self.body, self.body_start, self.body_goal, elapsed / self.settings.celebration_enter)
        elif elapsed <= hold_ends:
            self.body.set_points(self.body_goal.get_points().copy())
        else:
            _interpolate_shape(self.body, self.body_goal, self.body_start, (elapsed - hold_ends) / self.settings.celebration_exit)
        return True

    def update(self, time):
        if self.celebration is not None:
            started, _ = self.celebration
            exit_time = started + self.settings.celebration_enter + self.settings.celebration_hold
            if time >= exit_time and self.expression != "plain":
                self._set_mouth("plain", exit_time)
        if self._body_at(time):
            points = map_svg_points(self.body.get_points(), self.pi)
            plain = celebration_body_points("plain")
            target = self.body_goal.get_points()
            fixed = np.all(plain == target, axis=1)
            # Keep stationary legs exact even if the whole actor is transformed.
            points[fixed] = self.pi.body.get_points()[fixed]
            self.pi.body.set_points(points)
        if self.celebration is not None and time >= self.celebration[0] + self.settings.celebration_duration:
            self.celebration = None
            self.state = "ready"
            self.idle.release_focus(time)
            self.events.append((time, "celebration_finished", "plain"))
        self._mouth_at(time)
        self.pi.mouth.set_points(map_svg_points(self.mouth.get_points(), self.pi))


class FamilyBehavior(IdleMotion):
    """One scene clock composes body/mouth reactions before the gaze/blink layer."""

    def __init__(self, scene, characters, seed=None, settings=None, idle_settings=None):
        self.reactions = []
        self.reaction_settings = settings or ReactionSettings()
        super().__init__(scene, characters, seed=seed, settings=idle_settings)
        source = random.Random(f"family-reactions:{seed}") if seed is not None else random.Random()
        self.reactions = [
            CreatureReaction(controller.pi, controller, source.getrandbits(128), self.reaction_settings)
            for controller in self.controllers
        ]
        for actor in self.reactions:
            actor.pi.body.add_updater(_mark_face_dynamic)
            actor.pi.mouth.add_updater(_mark_face_dynamic)
        self.update()

    def _actor(self, pi):
        if not self.active:
            raise RuntimeError("The behavior controller has stopped.")
        for actor in self.reactions:
            if actor.pi is pi:
                return actor
        raise ValueError("This character is not managed by the controller.")

    def _time(self):
        return max(0.0, self.scene.get_time() - self.started)

    def ready(self, pi, new_round=False):
        return self._actor(pi).ready(self._time(), new_round=new_round)

    def waiting(self, pi):
        self._actor(pi).waiting(self._time())

    def parent_placed(self, pi):
        actor = self._actor(pi)
        if not actor.is_parent:
            raise ValueError("Only parents start another placement round.")
        return actor.ready(self._time(), new_round=True)

    def get_state(self, pi):
        return self._actor(pi).state

    def get_expression(self, pi):
        return self._actor(pi).expression

    def child_received(self, pi, fruit, look_target=None, mode=None):
        return self._actor(pi).received(fruit, self._time(), look_target=look_target, mode=mode)

    def update(self):
        if self.active:
            time = self._time()
            for actor in self.reactions:
                actor.update(time)
        super().update()

    def stop(self):
        if self.active:
            for actor in self.reactions:
                owns_body = actor.celebration is not None or actor.body_return is not None
                actor.celebration = actor.body_return = None
                if owns_body:
                    actor.pi.body.set_points(map_svg_points(celebration_body_points("plain"), actor.pi))
                actor.pi.mouth.set_points(map_svg_points(mouth_points("plain"), actor.pi))
                actor.idle.release_focus(self._time())
                actor.pi.body.remove_updater(_mark_face_dynamic)
                actor.pi.mouth.remove_updater(_mark_face_dynamic)
        super().stop()


def enable_behavior(scene, characters, seed=None, settings=None, idle_settings=None):
    return FamilyBehavior(scene, characters, seed=seed, settings=settings, idle_settings=idle_settings)
