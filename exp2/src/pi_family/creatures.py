"""Four characters built from 3Blue1Brown's SVG and PiCreature classes."""

from pathlib import Path

import numpy as np
from manimlib import DOWN, Line, UP, VGroup

from .upstream.pi_creature import BabyPiCreature, PiCreature, Randolph
from .upstream.pi_creature_animations import Blink


ASSETS = Path(__file__).resolve().parent / "assets"
FATHER_COLOR = "#176477"
MOTHER_COLOR = "#B83F49"
SON_COLOR = "#77C9EF"
DAUGHTER_COLOR = "#F27983"


class _PublicSVG:
    """Adapt the public six-part SVG to the author's current twelve-part loader.

    The body and mouth paths are unchanged. Eye drawing, curve subdivision,
    looking, flipping, and Baby proportions are handled by the upstream code.
    """

    def get_svg_file_path(self, mode):
        if mode != "plain":
            raise ValueError(
                "Only the original public 'plain' SVG is bundled. "
                "An additional original SVG is required for this pose."
            )
        return str(ASSETS / "PiCreatures_plain.svg")

    def init_structure(self):
        left_eye, right_eye, left_pupil, right_pupil, body, mouth = self.submobjects
        self.eyes = self.draw_eyes(
            VGroup(left_eye, right_eye), VGroup(left_pupil, right_pupil)
        )
        self.body = body
        self.mouth = mouth
        self.mouth.insert_n_curves(10)
        self.set_submobjects([self.eyes, self.body, self.mouth])


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
