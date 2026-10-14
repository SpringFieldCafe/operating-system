"""Invisible character-local anchors, independent of mouth shapes and blinks."""

import numpy as np
from manimlib import RIGHT, UP, VGroup, VectorizedPoint


def attach_face_frame(pi):
    center = pi.mouth.get_center()
    width = pi.mouth.get_width()
    pi.face_frame = VGroup(*[
        VectorizedPoint(point)
        for point in (center, center + width * RIGHT, center + width * UP)
    ])
    pi.add(pi.face_frame)


def frame_axes(pi):
    origin, right, up = [point.get_center() for point in pi.face_frame]
    return origin, right - origin, up - origin


def map_svg_points(points, pi):
    # Import lazily: the hand module also uses this mapping.
    from .hand_poses import source_geometry
    _, mouth, _ = source_geometry()
    delta = np.asarray(points) - mouth.get_center()
    origin, right, up = frame_axes(pi)
    return origin + delta[:, :1] * right / mouth.get_width() - delta[:, 1:2] * up / mouth.get_width()


def world_look_direction(point, pi, eye_center):
    origin, right, up = frame_axes(pi)
    world_center = origin + eye_center[0] * right + eye_center[1] * up
    delta = np.asarray(point) - world_center
    return np.array([np.dot(delta, right) / np.dot(right, right), np.dot(delta, up) / np.dot(up, up)])
