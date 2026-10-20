"""A fruit follows a sampled hand contour, without joining the actor's bounds."""

import numpy as np

from .face_frame import frame_axes
from .hand_poses import hand_tip, source_hand


class FruitAttachment:
    def __init__(self, pi, fruit, hand="left", offset=None, snap=True):
        if hand not in ("left", "right"):
            raise ValueError("Hand must be left or right.")
        if getattr(pi, "_fruit_attachment", None) is not None or getattr(fruit, "_hand_attachment", None) is not None:
            raise ValueError("Release the existing fruit attachment first.")
        if snap and pi.get_mode() == "plain":
            pi.change_mode(f"{source_hand(pi, hand)}_hand_hold")
        self.pi, self.fruit, self.hand = pi, fruit, hand
        self.active = True
        _, right, up = frame_axes(pi)
        basis = np.column_stack((right[:2], up[:2]))
        if offset is None:
            if snap:
                sign = -1 if hand == "left" else 1
                offset = np.array([sign * (fruit.get_width()/2 + 0.006), fruit.get_height()*0.2, 0])
            else:
                offset = fruit.get_center() - hand_tip(pi, hand)
        offset = np.asarray(offset, dtype=float)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError("Fruit offset must be a finite point.")
        self.local_offset = np.linalg.solve(basis, offset[:2])
        self.z_offset = offset[2]
        self.updater = lambda mob, dt: self.update()
        pi._fruit_attachment = self
        pi._active_hand = hand
        fruit._hand_attachment = self
        fruit.add_updater(self.updater)
        self.update()

    def update(self):
        if self.active:
            # A concurrent opacity/pose animation may have interpolated an old
            # bounding box. Align actual fruit points to the hand each frame.
            self.fruit.refresh_bounding_box(recurse_down=True)
            _, right, up = frame_axes(self.pi)
            offset = self.local_offset[0]*right + self.local_offset[1]*up
            offset[2] += self.z_offset
            self.fruit.move_to(hand_tip(self.pi, self.hand) + offset)

    def release(self):
        if self.active:
            self.update()
            self.fruit.remove_updater(self.updater)
            self.pi._fruit_attachment = None
            self.fruit._hand_attachment = None
            self.active = False
        return self.fruit


def carry_fruit(pi, fruit, hand="left", offset=None, snap=True):
    return FruitAttachment(pi, fruit, hand=hand, offset=offset, snap=snap)
