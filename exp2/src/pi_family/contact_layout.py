"""Place an existing Pi hand against its fruit, without changing the arm."""

from dataclasses import dataclass

import numpy as np
from manimlib import VMobject

from .creatures import DaughterPi, FatherPi, MotherPi, SonPi
from .hand_poses import source_geometry, arm_slice, source_hand
from .props import make_fruit_table


@dataclass(frozen=True)
class ContactRole:
    label: str
    creature_type: type
    height: float
    fruit: str
    side: int
    action: str

    @property
    def hand(self):
        return "right" if self.side == -1 else "left"


CONTACT_ROLES = {
    "father": ContactRole("爸爸", FatherPi, 2.4, "apple", 1, "放苹果"),
    "mother": ContactRole("妈妈", MotherPi, 2.16, "orange", -1, "放橘子"),
    "son": ContactRole("儿子", SonPi, 1.25, "orange", -1, "取橘子"),
    "daughter": ContactRole("女儿", DaughterPi, 1.25, "apple", 1, "取苹果"),
}
CONTACT_ABOVE_RIM = 0.17
CONTACT_GAP = 0.002


def sample_contour(mobject, samples_per_curve=25):
    """Sample ManimGL's actual quadratic curves, rather than their handles."""
    curves = np.array(list(mobject.get_bezier_tuples()))
    t = np.linspace(0, 1, samples_per_curve)[None, :, None]
    return ((1 - t)**2 * curves[:, 0, None]
            + 2 * (1 - t) * t * curves[:, 1, None]
            + t**2 * curves[:, 2, None]).reshape(-1, 3)


def hand_contour(pi, samples_per_curve=25, side="left"):
    arm = arm_slice(source_hand(pi, side))
    hand = VMobject().set_points(pi.body.get_points()[arm])
    return sample_contour(hand, samples_per_curve)


def outer_edges(contour, heights):
    """Maximum x on a contour at each height; NaN outside its vertical range."""
    a, b = contour[:-1, :2], contour[1:, :2]
    y = np.asarray(heights)[:, None]
    delta = b - a
    mask = ((y >= np.minimum(a[:, 1], b[:, 1]))
            & (y <= np.maximum(a[:, 1], b[:, 1]))
            & (np.abs(delta[:, 1]) > 1e-10))
    denom = np.where(np.abs(delta[:, 1]) > 1e-10, delta[:, 1], 1)
    xs = a[:, 0] + (y - a[:, 1]) * delta[:, 0] / denom
    result = np.max(np.where(mask, xs, -np.inf), axis=1)
    return np.where(np.isfinite(result), result, np.nan)


def make_contact_pose(role_key):
    """Return one character and the unchanged table/fruit group at contact.

    All roles retain the same orientation. Choose the hand facing the table,
    and fit the position to the unchanged fruit/plate geometry.
    """
    role = CONTACT_ROLES[role_key]
    props = make_fruit_table()
    pi = role.creature_type(height=role.height)
    pi._active_hand = role.hand
    pi.change_mode(f"{role.hand}_hand_place")
    hand = hand_contour(pi, 51, side=role.hand)
    outward_x = role.side * hand[:, 0]
    tip = hand[np.argmin(outward_x)]
    dy = props.plate.get_top()[1] + CONTACT_ABOVE_RIM - tip[1]
    target = getattr(props, role.fruit)
    constraints = []
    for part in target.family_members_with_points():
        contour = sample_contour(part, 51)
        contour[:, 0] *= role.side
        edges = outer_edges(contour, hand[:, 1] + dy)
        valid = np.isfinite(edges)
        if valid.any():
            constraints.append(np.max(edges[valid] - outward_x[valid]))
    dx = max(constraints) + CONTACT_GAP
    pi.shift([role.side * dx, dy, 0])
    return pi, props
