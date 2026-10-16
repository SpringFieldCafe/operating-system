"""Author reference poses and two locally drawn, mouth-only expressions."""

from functools import lru_cache
import xml.etree.ElementTree as ET

import numpy as np
import svgelements as se
from manimlib.mobject.svg.svg_mobject import VMobjectFromSVGPath
from manimlib.utils.iterables import index_within_group

from .expression_assets import reference_path
from .hand_poses import ASSETS, source_geometry


MOUTH_FILES = {
    "plain": "PiCreatures_plain.svg",
    "parent_smile": "PiCreatures_parent_smile.svg",
    "waiting": "PiCreatures_waiting.svg",
}
DRAWN_MOUTHS = {
    "parent_smile": "M246.3,144.8 C254,150.3 267.9,150.3 275.5,144.8 L275.2,148 C267.8,153.5 254.1,153.5 246,148 Z",
    "waiting": "M246.3,149.7 C254,145.2 267.9,145.2 275.5,149.7 L275.2,146.6 C267.8,142.1 254.1,142.1 246,146.6 Z",
}


def _paths(path):
    return list(ET.parse(path).getroot().iter("{http://www.w3.org/2000/svg}path"))


def generate_mouth_svgs():
    import re
    text = (ASSETS / MOUTH_FILES["plain"]).read_text(encoding="utf-8")
    matches = list(re.finditer(r'<path\b[^>]*\bd="([^"]*)"', text, re.DOTALL))
    mouth = matches[-1]
    for mode, drawing in DRAWN_MOUTHS.items():
        derived = text[:mouth.start(1)] + drawing + text[mouth.end(1):]
        derived = derived.replace("<!-- Generator:", f"<!-- Locally drawn {mode} mouth; see ../SOURCES.md. -->\n<!-- Generator:", 1)
        (ASSETS / MOUTH_FILES[mode]).write_text(derived, encoding="utf-8")


def _reference_paths(mode):
    return _paths(reference_path(mode))


def _translation(paths):
    original = se.Path(_paths(ASSETS / MOUTH_FILES["plain"])[4].attrib["d"])
    target = se.Path(paths[4].attrib["d"])
    return np.array([original[0].end.x - target[0].end.x, original[0].end.y - target[0].end.y, 0])


@lru_cache(maxsize=6)
def mouth_points(mode):
    reference = mode in ("happy", "hooray", "angry")
    paths = _reference_paths(mode) if reference else _paths(ASSETS / MOUTH_FILES[mode])
    mouth = VMobjectFromSVGPath(se.Path(paths[5].attrib["d"]))
    if reference:
        mouth.shift(_translation(paths))
    # All expressions keep one point count, including during saved hand animations.
    mouth.insert_n_curves(60 - mouth.get_num_curves())
    return mouth.get_points().copy()


@lru_cache(maxsize=2)
def angry_eye_points(index):
    """Reference eye silhouette, upright, one unit wide, with its bottom at 0.

    Each existing eye supplies its own width/position, preserving Baby sizing.
    The source's slanted upper contour supplies the angry eyelid shape.
    """
    if index not in (0, 1):
        raise ValueError("Choose eye 0 or 1.")
    eye = VMobjectFromSVGPath(se.Path(_reference_paths("angry")[index].attrib["d"]))
    points = eye.get_points().copy()
    points[:, 1] *= -1
    eye.set_points(points)
    origin = np.array([eye.get_x(), eye.get_bottom()[1], 0])
    return (points - origin) / eye.get_width()


def _reference_subdivision(reference, target, cuts=100):
    """Use ManimGL's subdivision allocation from the plain pose for both paths.

    Adapted from VMobject.insert_n_curves_to_point_list (ManimGL, MIT).
    This keeps the two original legs at the same curve indices throughout.
    """
    a0, handle, a1 = reference[:-1:2], reference[1::2], reference[2::2]
    lengths = np.linalg.norm(a1 - a0, axis=1)
    lengths[np.linalg.norm(handle - a0, axis=1) < 1e-6] = 0
    caps = ((len(lengths) + cuts) * lengths / lengths.sum()).astype(int)
    candidates = np.repeat(np.arange(len(lengths)), caps)
    piece_lengths = lengths[candidates] / (index_within_group(caps) + 1)
    best = np.argpartition(piece_lengths, -cuts)[-cuts:]
    counts = 1 + np.bincount(candidates[best], minlength=len(lengths))
    curve = np.repeat(np.arange(len(counts)), counts)
    width = (1.0 / counts[curve])[:, None]
    lower = width * index_within_group(counts)[:, None]
    ta0, th, ta1 = target[:-1:2], target[1::2], target[2::2]
    first = ta0[curve] + lower * (th[curve] - ta0[curve])
    second = th[curve] + lower * (ta1[curve] - th[curve])
    anchors = first + lower * (second - first)
    result = np.empty((2 * len(curve) + 1, 3))
    result[:-1:2] = anchors
    result[1::2] = anchors + width * (second - first)
    result[-1] = target[-1]
    return result.astype(np.float32)


@lru_cache(maxsize=3)
def celebration_body_points(mode):
    original, _, _ = source_geometry()
    if mode in ("plain", "happy"):
        # The reference happy body is the plain outline, translated in its SVG.
        return original.copy()
    if mode != "hooray":
        raise ValueError("Unknown celebration pose.")
    paths = _reference_paths(mode)
    base_path = se.Path(_paths(ASSETS / MOUTH_FILES["plain"])[4].attrib["d"])
    reference = VMobjectFromSVGPath(base_path).get_points().copy()
    target = VMobjectFromSVGPath(se.Path(paths[4].attrib["d"])).get_points().copy()
    target += _translation(paths)
    if target.shape != reference.shape or reference.shape != (83, 3):
        raise ValueError("Reference body curve structure changed.")
    # Six right-leg cubics and five left-leg cubics are unchanged anatomy.
    # Retain exact original vertices rather than tiny export-rounding differences.
    target[:27] = reference[:27]
    target[58:] = reference[58:]
    body = _reference_subdivision(reference, target)
    if body.shape != original.shape:
        raise ValueError("Celebration poses must retain the original body topology.")
    return body


if __name__ == "__main__":
    generate_mouth_svgs()
    print("Generated parent smile and waiting SVGs; only the original mouth path changed.")
