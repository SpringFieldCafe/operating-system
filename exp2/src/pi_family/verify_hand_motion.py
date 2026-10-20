"""Verify the hand-only constraint on actual ManimGL animation objects."""

import xml.etree.ElementTree as ET

import numpy as np
from manimlib import RIGHT, UP

from .creatures import DaughterPi, FatherPi, MotherPi, SonPi
from .hand_poses import ASSETS, POSE_FILES, source_geometry


def verify_svgs():
    def paths(mode):
        return list(ET.parse(ASSETS / POSE_FILES[mode]).getroot().iter(
            "{http://www.w3.org/2000/svg}path"
        ))

    original = paths("plain")
    body_path = original[4].attrib["d"]
    prefix = body_path[:body_path.index("H187.4") + len("H187.4")]
    suffix = body_path[body_path.index("h32.5"):]
    for mode in ("left_hand_reach", "left_hand_place"):
        target = paths(mode)
        assert len(target) == 6
        for index in (0, 1, 2, 3, 5):
            assert target[index].attrib == original[index].attrib
        assert target[4].attrib["d"].startswith(prefix)
        assert target[4].attrib["d"].endswith(suffix)


def verify_animation():
    raw_points, _, arm = source_geometry()
    tip_index = arm.start + int(np.argmin(raw_points[arm, 0]))
    for cls in (FatherPi, MotherPi, SonPi, DaughterPi):
        for mirrored in (False, True):
            pi = cls()
            if mirrored:
                pi.flip()
            pi.scale(0.8).shift(RIGHT + 0.2 * UP)
            original = pi.copy()
            body_points = pi.body.get_points().copy()
            fixed = np.ones(len(body_points), dtype=bool)
            fixed[arm] = False
            fixed[arm.start:arm.start + 4] = True
            fixed[arm.stop - 2:arm.stop] = True
            fixed_parts = [pi.eyes, pi.mouth]
            if hasattr(pi, "eyelashes"):
                fixed_parts.append(pi.eyelashes)
            snapshots = [part.get_all_points().copy() for part in fixed_parts]
            tip_positions = []

            for mode in ("left_hand_reach", "left_hand_place", "plain"):
                animation = pi.change(mode).build()
                animation.begin()
                for alpha in np.linspace(0, 1, 21):
                    animation.interpolate(float(alpha))
                    assert np.array_equal(pi.body.get_points()[fixed], body_points[fixed])
                    for part, points in zip(fixed_parts, snapshots):
                        assert np.array_equal(part.get_all_points(), points)
                    assert np.isfinite(pi.get_all_points()).all()
                animation.finish()
                assert pi.get_mode() == mode
                tip_positions.append(pi.body.get_points()[tip_index].copy())

            direction = 1 if mirrored else -1
            assert direction * (tip_positions[0][0] - body_points[tip_index][0]) > 0.04 * pi.body.get_height()
            assert tip_positions[0][1] > tip_positions[1][1]  # Lower gently to place.
            assert np.allclose(pi.body.get_points(), original.body.get_points(), atol=2e-6)


def main():
    verify_svgs()
    verify_animation()
    print("Verified original SVG segments and four mirrored/scaled roles; only the left arm moves at all 21 samples per phase.")


if __name__ == "__main__":
    main()
