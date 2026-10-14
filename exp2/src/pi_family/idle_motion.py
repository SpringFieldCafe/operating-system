"""Independent, continuous gaze and blink timelines for the four PiCreatures."""

from dataclasses import dataclass
import random

import numpy as np
from manimlib import Mobject, VGroup, smooth, there_and_back

from .upstream.pi_creature import PiCreature
from .upstream.pi_creature_animations import Blink


# Three separate short scan versions for each character, in character-local
# directions. (0, 0) means return to the middle of the eyes.
GAZE_VERSIONS = {
    "FatherPi": (
        ((-1, 0.15), (0.85, 0.1), (0, 0)),
        ((0.9, 0.35), (0.1, 0.7), (0, 0)),
        ((-0.8, -0.15), (-0.2, 0.55), (0, 0)),
    ),
    "MotherPi": (
        ((0.9, -0.3), (-0.75, -0.2), (0, 0)),
        ((-0.8, 0.35), (0.6, 0.2), (0, 0)),
        ((0.2, 0.65), (0.85, -0.1), (0, 0)),
    ),
    "SonPi": (
        ((-0.85, 0.65), (0.75, 0.5), (0, 0)),
        ((0.55, -0.4), (-0.85, 0.2), (0, 0)),
        ((0, 0.8), (0.9, 0.1), (0, 0)),
    ),
    "DaughterPi": (
        ((0.8, 0.55), (-0.7, 0.3), (0, 0)),
        ((-0.65, -0.3), (0.45, 0.65), (0, 0)),
        ((0.1, 0.85), (-0.85, 0.1), (0, 0)),
    ),
}
GAZE_AMOUNTS = {"FatherPi": 0.66, "MotherPi": 0.70, "SonPi": 0.83, "DaughterPi": 0.80}


@dataclass(frozen=True)
class IdleSettings:
    blink_interval: tuple[float, float] = (3.0, 5.0)
    blink_duration: float = 0.25
    look_duration: tuple[float, float] = (0.28, 0.42)
    look_hold: tuple[float, float] = (0.7, 1.3)
    scan_interval: tuple[float, float] = (3.0, 5.5)

    def __post_init__(self):
        for interval in (self.blink_interval, self.look_duration, self.look_hold, self.scan_interval):
            if not (0 < interval[0] <= interval[1]):
                raise ValueError("Idle timing ranges must be positive and ordered.")
        if not 0 < self.blink_duration < self.blink_interval[0]:
            raise ValueError("A blink must finish before the next blink can start.")


class _FaceRig(VGroup):
    """A virtual face, so Blink cannot overwrite the animated body or hand."""

    def __init__(self, pi):
        super().__init__()
        self.eyes = pi.eyes.copy()
        self.add(self.eyes)
        if hasattr(pi, "eyelashes"):
            self.eyelashes = pi.eyelashes.copy()
            self.add(self.eyelashes)

    def look(self, direction, amount=1.0):
        direction = np.array([*direction, 0.0])
        if np.linalg.norm(direction) > 0:
            PiCreature.look(self, direction)
            for eye in self.eyes:
                center = eye.iris.get_center()
                eye.pupil.move_to(center + amount * (eye.pupil.get_center() - center))
        else:
            # The author's look() normalizes a direction, so a central gaze
            # is handled explicitly instead of passing a zero vector to it.
            for eye in self.eyes:
                eye.pupil.move_to(eye.iris.get_center())
        return self

    def blink(self):
        bottom = self.eyes.get_y(np.array([0, -1, 0]))
        PiCreature.blink(self)
        if hasattr(self, "eyelashes"):
            for lash in self.eyelashes:
                points = lash.get_points().copy()
                points[:, 1] = bottom
                lash.set_points(points)
        return self


class CreatureIdle:
    """One creature's gaze and blink clocks, with separate random streams."""

    def __init__(self, pi, seed, settings):
        self.pi, self.settings = pi, settings
        random_source = random.Random(seed)
        self.blink_random = random.Random(random_source.getrandbits(128))
        self.gaze_random = random.Random(random_source.getrandbits(128))
        self.role = type(pi).__name__
        self.versions = GAZE_VERSIONS.get(self.role, GAZE_VERSIONS["FatherPi"])
        self.amount = GAZE_AMOUNTS.get(self.role, 0.7)

        reference = pi.copy()
        reference.clear_updaters()
        if reference.is_flipped():
            reference.flip(about_point=reference.mouth.get_center())
        self.reference_mouth = reference.mouth.get_center().copy()
        self.reference_width = reference.mouth.get_width()
        self.face = _FaceRig(reference)
        self.blink_started = -float("inf")
        self.next_blink = self.blink_random.uniform(*settings.blink_interval)
        self.next_gaze = self.gaze_random.uniform(0.8, 2.5)
        self.gaze_state = "choose"
        self.gaze_animation = None
        self.version_bag = []
        self.version_index = self.step_index = 0
        self.blink_events = []
        self.gaze_events = []
        self.last_time = 0.0

    def _advance_gaze(self, time):
        while self.next_gaze <= time:
            event_time = self.next_gaze
            if self.gaze_state in ("choose", "next"):
                if self.gaze_state == "choose":
                    if not self.version_bag:
                        self.version_bag = list(range(len(self.versions)))
                        self.gaze_random.shuffle(self.version_bag)
                    self.version_index = self.version_bag.pop()
                    self.step_index = 0
                direction = self.versions[self.version_index][self.step_index]
                duration = self.gaze_random.uniform(*self.settings.look_duration)
                self.gaze_animation = self.face.animate.look(direction, self.amount).build()
                self.gaze_animation.update_rate_info(run_time=duration, rate_func=smooth)
                self.gaze_animation.begin()
                self.gaze_started, self.gaze_duration = event_time, duration
                self.gaze_events.append((event_time, self.version_index, self.step_index))
                self.next_gaze = event_time + duration
                self.gaze_state = "finish"
            else:
                self.gaze_animation.finish()
                self.gaze_animation = None
                self.step_index += 1
                if self.step_index < len(self.versions[self.version_index]):
                    self.gaze_state = "next"
                    self.next_gaze = event_time + self.gaze_random.uniform(*self.settings.look_hold)
                else:
                    self.gaze_state = "choose"
                    self.next_gaze = event_time + self.gaze_random.uniform(*self.settings.scan_interval)
        if self.gaze_animation is not None:
            self.gaze_animation.interpolate((time - self.gaze_started) / self.gaze_duration)

    def _apply_face(self, face):
        scale = self.pi.mouth.get_width() / self.reference_width
        factors = np.array([-scale if self.pi.is_flipped() else scale, scale, 1.0])
        center = self.pi.mouth.get_center()
        parts = [(self.pi.eyes, face.eyes)]
        if hasattr(self.pi, "eyelashes"):
            parts.append((self.pi.eyelashes, face.eyelashes))
        for actual, virtual in parts:
            for destination, source in zip(actual.get_family(), virtual.get_family()):
                if source.has_points():
                    points = (source.get_points() - self.reference_mouth) * factors + center
                    destination.set_points(points)

    def update(self, time, blink=True):
        if time < self.last_time:
            raise ValueError("Idle animation time must move forwards.")
        self.last_time = time
        self._advance_gaze(time)
        while self.next_blink <= time:
            self.blink_started = self.next_blink
            self.blink_events.append(self.next_blink)
            self.next_blink += self.blink_random.uniform(*self.settings.blink_interval)

        face = self.face
        alpha = (time - self.blink_started) / self.settings.blink_duration
        if blink and 0 <= alpha < 1:
            face = self.face.copy()
            animation = Blink(face, rate_func=there_and_back, run_time=self.settings.blink_duration)
            animation.begin()
            animation.interpolate(alpha)
        self._apply_face(face)


def _mark_face_dynamic(mobject, dt):
    # The scene clock owns scheduling. This harmless marker makes ManimGL
    # redraw the face, and is safe when a hand animation copies a creature.
    pass


class IdleMotion:
    """Scene-level owner: one independent controller per creature, always active."""

    def __init__(self, scene, characters, seed=None, settings=None):
        if isinstance(characters, PiCreature):
            characters = (characters,)
        else:
            characters = tuple(characters)
        if not characters or len({id(pi) for pi in characters}) != len(characters):
            raise ValueError("Choose at least one creature, without duplicates.")
        if any(getattr(pi, "_ambient_face_active", False) for pi in characters):
            raise ValueError("A creature already has an active idle controller.")
        self.scene = scene
        self.started = scene.get_time()
        self.active = True
        source = random.Random(seed)
        settings = settings or IdleSettings()
        self.controllers = [CreatureIdle(pi, source.getrandbits(128), settings) for pi in characters]
        self.clock = Mobject()
        self.clock.add_updater(lambda clock, dt: self.update())
        for pi in characters:
            pi._ambient_face_active = True
            pi.eyes.add_updater(_mark_face_dynamic)
        scene.add(self.clock)
        self.update()

    def update(self):
        if self.active:
            time = max(0.0, self.scene.get_time() - self.started)
            for controller in self.controllers:
                controller.update(time)

    def stop(self):
        if self.active:
            time = max(0.0, self.scene.get_time() - self.started)
            for controller in self.controllers:
                controller.update(time, blink=False)
                controller.pi.eyes.remove_updater(_mark_face_dynamic)
                del controller.pi._ambient_face_active
            self.clock.clear_updaters()
            self.scene.remove(self.clock)
            self.active = False


def enable_idle(scene, characters, seed=None, settings=None):
    """Enable continuous independent face motion; a seed makes renders repeatable."""
    return IdleMotion(scene, characters, seed=seed, settings=settings)
