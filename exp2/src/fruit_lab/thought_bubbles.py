"""Quiet, head-anchored thought clouds with one detached cloud below."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from manimlib import SVGMobject, VGroup


# Each character's thought cloud sits toward the outer margin.
# Here direction describes the main cloud's offset, rather than a tail tip.
THOUGHT_DIRECTIONS = {"father": 1, "mother": -1, "son": -1, "daughter": 1}
# Phase radians per ambient second, independently varied by a further 2%.
# These 2t–3t comparison settings are an adaptation, not measured IMO parameters.
THOUGHT_PHASE_SPEEDS = {"father": (2.20, 2.70), "mother": (2.55, 2.10),
                        "son": (2.90, 2.40), "daughter": (2.35, 2.80)}


@lru_cache(maxsize=2)
def _reference_cloud(kind):
    # Reference-frame contours with rounded lobe subdivisions requested by the
    # user. Keep their original aspect ratios when sizing the two clouds.
    path = Path(__file__).with_name("assets") / f"thought_{kind}.svg"
    return SVGMobject(str(path))[0]


def cloud_outline(width, kind="main"):
    """Soften unevenness slightly, then uniformly scale the reference outline."""
    cloud = _reference_cloud(kind).copy()
    # Pull the reference toward its smooth elliptical envelope by only 18%.
    # The existing lobes remain; their unequal heights/depths are less stark.
    points = cloud.get_points().copy()
    center = cloud.get_center()
    radii = np.array([cloud.get_width(), cloud.get_height()]) / 2
    relative = points - center
    radial = np.linalg.norm(relative[:, :2] / radii, axis=1)
    relative[:, :2] *= (0.82 + 0.18 / np.maximum(radial, 0.1))[:, None]
    cloud.set_points(relative + center)
    cloud.set_shape(*list(2 * radii))
    cloud.set_width(width).move_to([0, 0, 0])
    cloud.set_fill("#000000", opacity=0.8).set_stroke("#FFFFFF", width=3)
    return cloud


class _LobeMotion:
    """A pure traveling angular wave around a fixed reference center."""
    wave_count = 6

    def __init__(self, outline, rng, amplitude, phase_speed=2.5):
        self.points = outline.get_points().copy()
        self.center = outline.get_center().copy()
        self.relative = self.points - self.center
        self.angles = np.arctan2(self.relative[:, 1], self.relative[:, 0])
        self.phase = rng.uniform(0, 2 * np.pi)
        self.phase_speed = rng.choice([-1.0, 1.0]) * phase_speed * rng.uniform(0.98, 1.02)
        self.amplitude = amplitude

    def wave_at(self, angles, elapsed):
        # Adapted from 3b1b's Superposition.undulating_bubble:
        # sin(6 * angle + time). The crest travels; the outline/text do not spin.
        return np.sin(self.wave_count * angles + self.phase_speed * elapsed + self.phase)

    def points_at(self, elapsed):
        wave = self.wave_at(self.angles, elapsed)
        stretch = 1 + self.amplitude * wave
        return self.center + self.relative * stretch[:, None]


class ThoughtCloud(VGroup):
    def __init__(self, content, head, direction, child=False, seed=None, phase_speeds=(2.5, 2.7)):
        super().__init__()
        self.direction = direction
        self.head = np.array(head, dtype=float).copy()
        # Reduce empty space around the fixed text while keeping the reference
        # contour's proportions. The detached cloud keeps its existing size.
        self.cloud = cloud_outline(0.85 * max(2.35, content.get_width() + 0.95))
        lift = 0 if child else 0.05  # Parents' main clouds rise another 4 px.
        self.center = self.head + np.array([direction * (1.65 if child else 0.95),
                                           (0.43 if child else 0.94) + lift, 0])
        self.cloud.move_to(self.center)
        self.connector = cloud_outline(0.345, kind="connector").set_stroke(width=2)
        # Position the small cloud in the visible gap, slightly toward the
        # large contour. Use its nearest edge rather than its distant center.
        edge = np.array([self.cloud.quick_point_from_proportion(alpha)
                         for alpha in np.linspace(0, 1, 128, endpoint=False)])
        nearest = edge[np.argmin(np.linalg.norm(edge - self.head, axis=1))]
        self.connector.move_to(self.head + 0.55 * (nearest - self.head))
        self.body = VGroup(self.connector, self.cloud)
        self.content = content.move_to(self.center)
        self.add(self.body, self.content)
        # Appearance randomness never participates in process scheduling.
        rng = np.random.default_rng(seed)
        self.motion_seeds = tuple(int(value) for value in rng.integers(0, 2**63 - 1, size=2))
        self._main_motion = _LobeMotion(self.cloud, np.random.default_rng(self.motion_seeds[0]),
                                        amplitude=0.028, phase_speed=phase_speeds[0])
        self._connector_motion = _LobeMotion(self.connector, np.random.default_rng(self.motion_seeds[1]),
                                             amplitude=0.04, phase_speed=phase_speeds[1])
        # Draw the entrance from the already independent initial shapes. Motion
        # then continues from those shapes without a shared start or a jump.
        self.cloud.set_points(self._main_motion.points_at(0))
        self.connector.set_points(self._connector_motion.points_at(0))
        self._motion_start = None

    def update_motion(self, ambient_time):
        # Run only after DrawBorderThenFill/Write finish. Deforming a partially
        # drawn path would reveal the full outline ahead of its entrance.
        if self._motion_start is None:
            self._motion_start = ambient_time
            self._content_points = [(part, part.get_points().copy())
                                    for part in self.content.family_members_with_points()]
        elapsed = max(0, ambient_time - self._motion_start)
        self.cloud.set_points(self._main_motion.points_at(elapsed))
        self.connector.set_points(self._connector_motion.points_at(elapsed))
        # Keep completed glyphs at their fixed anchor throughout the wave.
        for part, original in self._content_points:
            part.set_points(original)
