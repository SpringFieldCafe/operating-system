"""Four characters built from 3Blue1Brown's SVG and PiCreature classes."""

from pathlib import Path

import numpy as np
from manimlib import DOWN, Line, UP, VGroup
from manimlib.animation.transform import _MethodAnimation
from manimlib.mobject.mobject import _AnimationBuilder

from .hand_poses import POSE_FILES, body_points_for_character, source_geometry
from .upstream.pi_creature import BabyPiCreature, PiCreature, Randolph
from .upstream.pi_creature_animations import Blink


ASSETS = Path(__file__).resolve().parent / "assets"
FATHER_COLOR = "#176477"
MOTHER_COLOR = "#B83F49"
SON_COLOR = "#77C9EF"
DAUGHTER_COLOR = "#F27983"


class _PoseAnimation(_MethodAnimation):
    def interpolate_submobject(self, submob, start, target, alpha):
        super().interpolate_submobject(submob, start, target, alpha)
        original_points = start.get_points()
        target_points = target.get_points()
        if original_points.shape == target_points.shape and len(original_points):
            unchanged = np.all(original_points == target_points, axis=1)
            if unchanged.any():
                points = submob.get_points().copy()
                # Ordinary float32 lerp can round even identical endpoints.
                # Stationary vertices are copied exactly on every frame.
                points[unchanged] = original_points[unchanged]
                submob.set_points(points)

    def finish(self):
        super().finish()
        # Recent ManimGL skips align_data_and_family for already aligned poses.
        # Keep the mode name in sync without changing any interpolation geometry.
        self.mobject.mode = self.target_mobject.mode


class _PoseBuilder(_AnimationBuilder):
    def build(self):
        return _PoseAnimation(self.mobject, self.methods, **self.anim_args)


class _PublicSVG:
    """Adapt the public six-part SVG to the author's current twelve-part loader.

    The body and mouth paths are unchanged. Eye drawing, curve subdivision,
    looking, flipping, and Baby proportions are handled by the upstream code.
    """

    def __init__(self, mode="plain", **kwargs):
        super().__init__(mode=mode, **kwargs)
        if mode != "plain":
            # Body-only retopology: the author subdivides SVG curves according
            # to length. A stretched arm would otherwise redistribute points
            # on the stationary legs and right side during interpolation.
            self.body.set_points(body_points_for_character(mode, self))

    def get_svg_file_path(self, mode):
        if mode not in POSE_FILES:
            raise ValueError(
                f"Available SVG poses: {', '.join(POSE_FILES)}. "
                "Other poses require an additional SVG."
            )
        return str(ASSETS / POSE_FILES[mode])

    def init_structure(self):
        left_eye, right_eye, left_pupil, right_pupil, body, mouth = self.submobjects
        self.eyes = self.draw_eyes(
            VGroup(left_eye, right_eye), VGroup(left_pupil, right_pupil)
        )
        self.body = body
        self.mouth = mouth
        self.mouth.insert_n_curves(10)
        self.set_submobjects([self.eyes, self.body, self.mouth])

    def change_mode(self, mode):
        body_points = self.body.get_points().copy()
        fixed_parts = [(self.eyes, self.eyes.copy()), (self.mouth, self.mouth.copy())]
        if hasattr(self, "eyelashes"):
            fixed_parts.append((self.eyelashes, self.eyelashes.copy()))
        if getattr(self, "_ambient_face_active", False):
            # The author's height/eye alignment must use an open-eyed pose:
            # a blink temporarily shrinks the face bounds. Normalize only the
            # preparation copy, then restore its current visible face below.
            reference = self.__class__()
            reference.scale(self.body.get_height() / reference.body.get_height())
            if self.is_flipped() != reference.is_flipped():
                reference.flip()
            reference.shift(self.mouth.get_center() - reference.mouth.get_center())
            self.eyes.become(reference.eyes)
            if hasattr(self, "eyelashes"):
                self.eyelashes.become(reference.eyelashes)
        super().change_mode(mode)
        _, _, arm = source_geometry()
        target_points = self.body.get_points().copy()
        # Preserve non-arm points exactly, including after mirroring or scaling.
        target_points[:arm.start] = body_points[:arm.start]
        target_points[arm.stop:] = body_points[arm.stop:]
        # Preserve the original zero-length shoulder marker as well as both
        # attachment tangents. Perturbing a marker changes path segmentation.
        target_points[arm.start:arm.start + 4] = body_points[arm.start:arm.start + 4]
        target_points[arm.stop - 2:arm.stop] = body_points[arm.stop - 2:arm.stop]
        self.body.set_points(target_points)
        for part, original in fixed_parts:
            part.become(original)
        return self

    def change(self, new_mode, look_at=None):
        animation = _PoseBuilder(self).change_mode(new_mode)
        if look_at is not None:
            animation = animation.look_at(look_at)
        return animation


def _make_eyelashes(pi):
    """Attach three short lashes to the actual upper outer contour of each eye."""
    lashes = VGroup()
    for eye in pi.eyes:
        iris = eye.iris
        side = -1 if iris.get_x() < pi.eyes.get_x() else 1
        center = iris.get_center()
        radii = np.array([iris.get_width() / 2, iris.get_height() / 2, 0])
        contour = np.array([iris.pfp(t) for t in np.linspace(0, 1, 160)])
        for angle in (42, 62, 82):
            theta = np.deg2rad(angle if side == 1 else 180 - angle)
            direction = np.array([np.cos(theta), np.sin(theta), 0])
            ideal_start = center + radii * direction
            start = contour[np.argmin(np.linalg.norm(contour - ideal_start, axis=1))]
            end = start + 0.30 * iris.get_height() * direction
            # A muted pink keeps the fine lashes visible above the white eyes
            # on the dark background used in the author's animation style.
            lashes.add(Line(start, end, stroke_color="#DCA0AD", stroke_width=2.4))
    return lashes


class _Eyelashes:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A sibling of the eyes preserves the author's two-part eye structure
        # and pupil movement bounds. It still belongs to the same character.
        self.eyelashes = _make_eyelashes(self)
        self.add(self.eyelashes)

    def blink(self):
        bottom_y = self.eyes.get_y(DOWN)
        super().blink()
        # Blink's there_and_back interpolation restores both eyes and lashes.
        for lash in self.eyelashes:
            points = lash.get_points().copy()
            points[:, 1] = bottom_y
            lash.set_points(points)
        return self


class FatherPi(_PublicSVG, Randolph):
    """Original adult proportions, with a slightly deeper version of BLUE_E."""

    def __init__(self, mode="plain", color=FATHER_COLOR, height=3.0, **kwargs):
        super().__init__(mode=mode, color=color, height=height, **kwargs)


class MotherPi(_Eyelashes, _PublicSVG, PiCreature):
    """Adult Pi at 90% of Father's height, deep red, with eyelashes only."""

    def __init__(self, mode="plain", color=MOTHER_COLOR, height=2.7, **kwargs):
        super().__init__(mode=mode, color=color, height=height, **kwargs)


class SonPi(_PublicSVG, BabyPiCreature):
    """The author's unchanged Baby constructor, in sky blue."""

    def __init__(self, mode="plain", color=SON_COLOR, height=1.5, **kwargs):
        super().__init__(mode=mode, color=color, height=height, **kwargs)


class DaughterPi(_Eyelashes, _PublicSVG, BabyPiCreature):
    """The same Baby proportions as Son, in light red, with eyelashes only."""

    def __init__(self, mode="plain", color=DAUGHTER_COLOR, height=1.5, **kwargs):
        super().__init__(mode=mode, color=color, height=height, **kwargs)


def make_family():
    """Return Father, Mother, Son, Daughter; align the bottoms of their bodies."""
    family = VGroup(FatherPi(), MotherPi(), SonPi(), DaughterPi())
    for pi, x in zip(family, (-4.7, -1.45, 1.65, 4.6)):
        pi.set_x(x)
        pi.shift((-1.25 - pi.body.get_bottom()[1]) * UP)
    return family
