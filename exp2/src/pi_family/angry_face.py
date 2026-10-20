"""Compose reference angry eye silhouettes over the unchanged gaze timeline."""

import numpy as np
from manimlib import VMobject

from .expression_geometry import angry_eye_points


def _ring(mobject, count=128):
    # Arc-length samples remove the reference SVG's unequal curve spacing.
    points = mobject.get_points()
    a, handle, b = points[:-1:2], points[1::2], points[2::2]
    t = np.linspace(0, 1, 49)[None, :, None]
    contour = ((1-t)**2*a[:, None]+2*(1-t)*t*handle[:, None]+t**2*b[:, None]).reshape(-1, 3)
    contour = np.vstack((contour, contour[0]))
    distances = np.r_[0, np.cumsum(np.linalg.norm(np.diff(contour, axis=0), axis=1))]
    distances, indices = np.unique(distances, return_index=True)
    targets = np.linspace(0, distances[-1], count, endpoint=False)
    return np.column_stack([np.interp(targets, distances, contour[indices, axis]) for axis in range(3)])


def _quadratics(ring):
    anchors, middle = ring[::2], ring[1::2]
    ends = np.roll(anchors, -1, axis=0)
    points = np.empty((2*len(anchors)+1, 3))
    points[:-1:2] = anchors
    points[1::2] = 2*middle - (anchors+ends)/2
    points[-1] = anchors[0]
    return points


def _normals(polygon):
    edges = np.roll(polygon, -1, axis=0)-polygon
    area = np.sum(polygon[:, 0]*np.roll(polygon[:, 1], -1)
                  - polygon[:, 1]*np.roll(polygon[:, 0], -1))
    normals = np.sign(area)*np.column_stack((-edges[:, 1], edges[:, 0]))
    return normals/np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


def _confine_pupil(eye, normal_polygon, normal_normals, amount):
    # Project the existing pupil inside the new silhouette; retain its size,
    # highlight and gaze direction as far as the lowered eyelid allows.
    polygon = eye.iris.get_points()[:-1:2, :2]
    normals = _normals(polygon)
    center = eye.pupil.get_center().copy()
    radius = eye.pupil.get_width()/2
    # The author's large Baby pupils can slightly overlap the normal iris.
    # Tighten this clearance with the expression, rather than snapping the
    # pupils inward on the first nonzero anger frame (or on recovery).
    normal_gap = np.sum((center[:2]-normal_polygon)*normal_normals, axis=1).min()
    initial_radius = np.clip(normal_gap, 0, radius)
    radius = (1-amount)*initial_radius+amount*radius
    for _ in range(64):
        gaps = np.sum((center[:2]-polygon)*normals, axis=1)-radius
        worst = int(np.argmin(gaps))
        if gaps[worst] >= -1e-8:
            break
        center[:2] -= gaps[worst]*normals[worst]
    eye.pupil.shift(center-eye.pupil.get_center())


class AngryEyes:
    """Cached contours; only the composed copy changes, never the gaze rig."""

    def __init__(self, face):
        self.eyes, self.lashes = [], []
        for index, eye in enumerate(face.eyes):
            iris = eye.iris
            normal = _ring(iris)
            target = VMobject().set_points(angry_eye_points(index)*iris.get_width()
                                          + [iris.get_x(), iris.get_bottom()[1], 0])
            target = _ring(target)
            candidates = [np.roll(direction, shift, axis=0)
                          for direction in (target, target[::-1]) for shift in range(len(target))]
            goal = min(candidates, key=lambda points: np.sum((points-normal)**2))
            normal_points = _quadratics(normal)
            self.eyes.append((normal_points, _quadratics(goal), _normals(normal_points[:-1:2, :2])))
            if hasattr(face, "eyelashes"):
                for lash in face.eyelashes[index*3:index*3+3]:
                    root = lash.get_points()[0]
                    nearest = int(np.argmin(np.linalg.norm(normal-root, axis=1)))
                    self.lashes.append(goal[nearest]-normal[nearest])

    def apply(self, face, amount):
        for eye, (normal, goal, normals) in zip(face.eyes, self.eyes):
            eye.iris.set_points((1-amount)*normal+amount*goal)
            _confine_pupil(eye, normal[:-1:2, :2], normals, amount)
        if hasattr(face, "eyelashes"):
            for lash, delta in zip(face.eyelashes, self.lashes):
                lash.shift(amount*delta)
        return face
