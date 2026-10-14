"""Derive two SVG poses by changing only the original protruding left arm."""

from functools import lru_cache
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
import svgelements as se
from manimlib.mobject.svg.svg_mobject import VMobjectFromSVGPath


ASSETS = Path(__file__).resolve().parent / "assets"
POSE_FILES = {
    "plain": "PiCreatures_plain.svg",
    "left_hand_reach": "PiCreatures_left_hand_reach.svg",
    "left_hand_place": "PiCreatures_left_hand_place.svg",
}
SHOULDER_TOP = np.array([187.4, 126.5, 0])
SHOULDER_BOTTOM = np.array([182.9, 157.3, 0])


def _paths(mode):
    root = ET.parse(ASSETS / POSE_FILES[mode]).getroot()
    return list(root.iter("{http://www.w3.org/2000/svg}path"))


def _arm_slice(points):
    indices = []
    for shoulder in (SHOULDER_TOP, SHOULDER_BOTTOM):
        distances = np.linalg.norm(points - shoulder, axis=1)
        index = int(np.argmin(distances))
        if distances[index] > 0.0001:
            raise ValueError("SVG is missing an unchanged shoulder anchor.")
        indices.append(index)
    return slice(indices[0], indices[1] + 1)


@lru_cache(maxsize=1)
def source_geometry():
    paths = _paths("plain")
    body = VMobjectFromSVGPath(se.Path(paths[4].attrib["d"]))
    # The same subdivision the author's PiCreature constructor applies.
    body.insert_n_curves(100)
    mouth = VMobjectFromSVGPath(se.Path(paths[5].attrib["d"]))
    mouth.insert_n_curves(10)
    return body.get_points().copy(), mouth, _arm_slice(body.get_points())


@lru_cache(maxsize=3)
def pose_body_points(mode):
    """Use the same point indices in every pose; all non-arm points stay exact."""
    original, _, arm = source_geometry()
    points = original.copy()
    if mode != "plain":
        path = _paths(mode)[4].attrib["d"]
        # Read the SVG's explicit quadratic nodes, including its zero-length
        # shoulder marker. Manim's SVG parser drops that marker; keeping it
        # here preserves the original body's point correspondence exactly.
        nodes = []
        for segment in se.Path(path):
            if not isinstance(segment, se.QuadraticBezier):
                continue
            start = np.array([segment.start.x, segment.start.y, 0])
            if not nodes and not np.allclose(start, SHOULDER_TOP, atol=0.0001):
                continue
            if not nodes:
                nodes.append(start)
            nodes.extend((
                [segment.control.x, segment.control.y, 0],
                [segment.end.x, segment.end.y, 0],
            ))
            if np.allclose(nodes[-1], SHOULDER_BOTTOM, atol=0.0001):
                break
        target_arm = np.array(nodes)
        if len(target_arm) != len(points[arm]):
            raise ValueError("Left arm poses must have identical curve topology.")
        points[arm] = target_arm
        points[arm.start:arm.start + 4] = original[arm.start:arm.start + 4]
        points[arm.stop - 2:arm.stop] = original[arm.stop - 2:arm.stop]
    return points


def body_points_for_character(mode, character):
    """Map SVG coordinates using the fixed face frame (mouth at construction)."""
    if hasattr(character, "face_frame"):
        from .face_frame import map_svg_points
        return map_svg_points(pose_body_points(mode), character)
    _, source_mouth, _ = source_geometry()
    scale = character.mouth.get_width() / source_mouth.get_width()
    factors = np.array([-scale if character.is_flipped() else scale, -scale, 0])
    return (
        (pose_body_points(mode) - source_mouth.get_center()) * factors
        + character.mouth.get_center()
    )


def generate_svgs():
    """Preserve every other original SVG path and body segment verbatim."""
    text = (ASSETS / POSE_FILES["plain"]).read_text(encoding="utf-8")
    match = re.search(r'<path class="st1" d="([^"]*)"', text, re.DOTALL)
    if match is None:
        raise ValueError("The original six-part SVG body was not found.")
    body_path = match.group(1)
    start = body_path.index("H187.4") + len("H187.4")
    end = body_path.index("h32.5", start)
    original, _, arm = source_geometry()
    arm_points = original[arm].copy()

    # The two shoulder anchors and their tangent handles remain fixed.
    root_fraction = np.clip((arm_points[:, 1] - 126.5) / 30.8, 0, 1)
    root_x = 187.4 - 4.5 * root_fraction
    t = np.clip((root_x - arm_points[:, 0]) / 87.2, 0, 1)
    weights = t * t * (3 - 2 * t)
    # The first quadratic is the original zero-length shoulder marker;
    # the following handle gives the actual horizontal attachment tangent.
    weights[:4] = weights[-2:] = 0

    for mode, displacement in (
        ("left_hand_reach", [-22, -46, 0]),
        ("left_hand_place", [-27, -22, 0]),
    ):
        points = arm_points + weights[:, None] * np.array(displacement)
        points[:3], points[-1] = SHOULDER_TOP, SHOULDER_BOTTOM
        commands = " ".join(
            f"Q{handle[0]:.7f},{handle[1]:.7f} {anchor[0]:.7f},{anchor[1]:.7f}"
            for handle, anchor in zip(points[1::2], points[2::2])
        )
        new_path = body_path[:start] + commands + body_path[end:]
        new_text = text[:match.start(1)] + new_path + text[match.end(1):]
        new_text = new_text.replace(
            "<!-- Generator:",
            "<!-- Derived left-hand pose; see ../SOURCES.md. -->\n<!-- Generator:",
            1,
        )
        (ASSETS / POSE_FILES[mode]).write_text(new_text, encoding="utf-8")
    pose_body_points.cache_clear()
    print("Generated reach/place SVGs; only the protruding left-arm path was replaced.")


if __name__ == "__main__":
    generate_svgs()
