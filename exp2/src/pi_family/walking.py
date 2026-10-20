"""Small alternating steps on the existing SVG; no flips or pose replacement."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from manimlib import Animation, smooth

from .face_frame import frame_axes, map_svg_points
from .hand_poses import arm_slice, source_geometry, source_hand


@dataclass(frozen=True)
class WalkSettings:
    # Fractions of standing body height. One stride contains two footfalls.
    stride: float = 0.55
    foot_lift: float = 0.055
    body_bob: float = 0.018
    arm_swing: float = 0.035
    speed: float = 0.9

    def __post_init__(self):
        if not all(np.isfinite(v) and v > 0 for v in vars(self).values()):
            raise ValueError("Walk settings must be finite and positive.")


@lru_cache(maxsize=1)
def leg_slices():
    points, _, _ = source_geometry()
    def index(point):
        return int(np.argmin(np.linalg.norm(points - point, axis=1)))
    return (slice(index([292.8, 157.1, 0]), index([305.9, 157.2, 0]) + 1),
            slice(index([215.4, 157.3, 0]), len(points)))


def standing_point(pi):
    """Fixed midpoint between the feet, independent of current leg/face motion."""
    return map_svg_points(np.array([[221.9, 377.8, 0]]), pi)[0]


def _body_height(pi):
    source, mouth, _ = source_geometry()
    return np.ptp(source[:, 1]) * np.linalg.norm(frame_axes(pi)[2]) / mouth.get_width()


def _unmap(points, pi):
    _, mouth, _ = source_geometry()
    origin, right, up = frame_axes(pi)
    basis = np.column_stack((right[:2], -up[:2])) / mouth.get_width()
    local = np.linalg.solve(basis, (points[:, :2] - origin[:2]).T).T
    return np.column_stack((local, np.zeros(len(points)))) + mouth.get_center()


def _foot_phase(phase, stride, height):
    """A planted stance followed by a smooth raised return to the next step."""
    phase %= 1.0
    if phase < 0.5:
        return stride * (0.25 - phase), 0.0
    swing = 2 * phase - 1
    return stride * (-0.25 + 0.5 * smooth(swing)), height * np.sin(np.pi * swing)**2


class WalkTo(Animation):
    """Move the standing_point to destination; distance drives the gait phase.

    Faces keep their current live updater state. A held hand keeps its local
    pose; only free arms swing. Do not animate another body pose concurrently
    on this same actor; finish its take/celebration before starting a walk.
    """

    def __init__(self, pi, destination, run_time=None, settings=None, **kwargs):
        self.destination = np.asarray(destination, dtype=float)
        if self.destination.shape != (3,) or not np.isfinite(self.destination).all():
            raise ValueError("Destination must be a finite three-dimensional point.")
        self.settings = settings or WalkSettings()
        distance = np.linalg.norm((self.destination - standing_point(pi))[:2])
        duration = max(0.25, distance / (self.settings.speed * _body_height(pi))) if run_time is None else run_time
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError("Walk duration must be finite and positive.")
        super().__init__(pi, run_time=duration, **kwargs)

    def begin(self):
        pi = self.mobject
        if getattr(pi, "_body_reaction_active", False):
            raise ValueError("Finish the celebration before walking.")
        self.displacement = self.destination - standing_point(pi)
        self.distance = np.linalg.norm(self.displacement[:2])
        self.direction = self.displacement[:2] / self.distance if self.distance else np.array([1., 0.])
        self.height = _body_height(pi)
        self.original_body = pi.body.get_points().copy()
        self.canonical = _unmap(self.original_body, pi)
        self.applied = np.zeros(3)
        attachment = getattr(pi, "_fruit_attachment", None)
        self.held_hand = attachment.hand if attachment is not None and attachment.active else None
        super().begin()

    def interpolate_mobject(self, alpha):
        alpha = float(np.clip(self.time_spanned_alpha(alpha), 0, 1))
        progress = self.rate_func(alpha)
        stride = self.settings.stride * self.height
        phase = progress * self.distance / stride
        envelope = smooth(min(alpha / 0.14, 1)) * smooth(min((1-alpha) / 0.14, 1))
        if not self.distance:
            envelope = 0
        bob = self.settings.body_bob * self.height * envelope * np.sin(2*np.pi*phase)**2
        desired = progress * self.displacement + np.array([0, bob, 0])
        pi = self.mobject
        pi.shift(desired - self.applied)
        self.applied = desired
        if alpha in (0, 1):
            pi.body.set_points(self.original_body + desired)
            return
        points = map_svg_points(self.canonical, pi)
        source, _, _ = source_geometry()
        for leg, offset in zip(leg_slices(), (0, 0.5)):
            base = source[leg]
            t = np.clip((base[:, 1] - 157.3) / (377.8 - 157.3), 0, 1)
            weights = t*t*(3-2*t)
            weights[:4] = weights[-2:] = 0
            horizontal, lift = _foot_phase(phase + offset, stride, self.settings.foot_lift * self.height)
            delta = envelope * horizontal * self.direction + np.array([0, envelope * lift - bob])
            points[leg, :2] += weights[:, None] * delta
        for side, offset in (("left", 0), ("right", 0.5)):
            if side == self.held_hand:
                continue
            arm = arm_slice(source_hand(pi, side))
            base = source[arm]
            root = 0.5 * (base[0, 0] + base[-1, 0])
            t = np.abs(base[:, 0] - root)
            t = np.clip(t / t.max(), 0, 1)
            weights = t*t*(3-2*t)
            weights[:4] = weights[-2:] = 0
            swing = self.settings.arm_swing * self.height * envelope * np.sin(2*np.pi*(phase + offset))
            points[arm, 1] += weights * swing
        pi.body.set_points(points)


def walk_to(scene, pi, destination, run_time=None, settings=None):
    scene.play(WalkTo(pi, destination, run_time=run_time, settings=settings))
