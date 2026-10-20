"""Hand poses on the original asymmetric outline, with stable curve indices."""

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
    "right_hand_reach": "PiCreatures_right_hand_reach.svg",
    "right_hand_place": "PiCreatures_right_hand_place.svg",
    "left_hand_hold": "PiCreatures_left_hand_hold.svg",
    "right_hand_hold": "PiCreatures_right_hand_hold.svg",
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


@lru_cache(maxsize=2)
def arm_slice(side):
    original, _, left = source_geometry()
    if side == "left":
        return left
    if side != "right":
        raise ValueError("Hand must be left or right.")
    # The right arm starts at its lower shoulder and ends on the straight
    # upper bar. Pick an existing anchor, keeping the original topology.
    start = int(np.argmin(np.linalg.norm(original - [305.9, 157.2, 0], axis=1)))
    upper = np.flatnonzero((original[:, 1] == 126.5) & (np.arange(len(original)) % 2 == 0))
    end = int(upper[np.argmin(abs(original[upper, 0] - 305.9))])
    return slice(start, end + 1)


def source_hand(pi, screen_side):
    if screen_side not in ("left", "right"):
        raise ValueError("Hand must be left or right.")
    if pi.is_flipped():
        return "right" if screen_side == "left" else "left"
    return screen_side


def hand_tip(pi, side="left"):
    """A sampled contour point on the requested screen-side hand."""
    points = pi.body.get_points()[arm_slice(source_hand(pi, side))]
    curves = np.stack((points[:-1:2], points[1::2], points[2::2]), axis=1)
    t = np.linspace(0, 1, 25)[None, :, None]
    contour = ((1-t)**2 * curves[:, 0, None] + 2*(1-t)*t*curves[:, 1, None]
               + t**2 * curves[:, 2, None]).reshape(-1, 3)
    direction = -1 if side == "left" else 1
    return contour[np.argmax(direction * contour[:, 0])].copy()


@lru_cache(maxsize=7)
def pose_body_points(mode):
    """Use the same point indices in every pose; all non-arm points stay exact."""
    original, _, _ = source_geometry()
    points = original.copy()
    if mode != "plain":
        side = mode.split("_", 1)[0]
        arm = arm_slice(side)
        shoulder_start, shoulder_end = original[arm.start], original[arm.stop - 1]
        path = _paths(mode)[4].attrib["d"]
        # Read the SVG's explicit quadratic nodes, including its zero-length
        # shoulder marker. Manim's SVG parser drops that marker; keeping it
        # here preserves the original body's point correspondence exactly.
        nodes = []
        for segment in se.Path(path):
            if not isinstance(segment, se.QuadraticBezier):
                continue
            start = np.array([segment.start.x, segment.start.y, 0])
            if not nodes and not np.allclose(start, shoulder_start, atol=0.0001):
                continue
            if not nodes:
                nodes.append(start)
            nodes.extend((
                [segment.control.x, segment.control.y, 0],
                [segment.end.x, segment.end.y, 0],
            ))
            if np.allclose(nodes[-1], shoulder_end, atol=0.0001):
                break
        target_arm = np.array(nodes)
        if len(target_arm) != len(points[arm]):
            raise ValueError("Hand poses must have identical curve topology.")
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
        ("left_hand_hold", [0, -66, 0]),
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


def generate_right_svgs():
    """Derive the right poses without mirroring either the body or left arm."""
    text = (ASSETS / POSE_FILES["plain"]).read_text(encoding="utf-8")
    match = re.search(r'<path class="st1" d="([^"]*)"', text, re.DOTALL)
    path = match.group(1)
    start = path.index("h63.8")
    end = path.index("H187.4", start)
    original, _, _ = source_geometry()
    arm = arm_slice("right")
    base = original[arm]
    root_x = max(base[0, 0], base[-1, 0])
    t = np.clip((base[:, 0] - root_x) / (base[:, 0].max() - root_x), 0, 1)
    weights = t*t*(3-2*t)
    weights[:4] = weights[-2:] = 0
    for mode, delta in (("right_hand_reach", [22, 24, 0]),
                        ("right_hand_place", [27, 48, 0]),
                        ("right_hand_hold", [0, 4, 0])):
        points = base + weights[:, None] * delta
        commands = " ".join(f"Q{h[0]:.7f},{h[1]:.7f} {a[0]:.7f},{a[1]:.7f}"
                            for h, a in zip(points[1::2], points[2::2]))
        new_path = path[:start] + commands + path[end:]
        derived = text[:match.start(1)] + new_path + text[match.end(1):]
        derived = derived.replace("<!-- Generator:",
                                  "<!-- Derived right-hand pose; see ../SOURCES.md. -->\n<!-- Generator:", 1)
        (ASSETS / POSE_FILES[mode]).write_text(derived, encoding="utf-8")
    pose_body_points.cache_clear()
    print("Generated right reach/place SVGs on the original right-arm contour.")


if __name__ == "__main__":
    generate_svgs()
    generate_right_svgs()
