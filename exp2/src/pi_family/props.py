"""Small, hollow 2D props built directly with ManimGL geometry."""

import numpy as np
from manimlib import Circle, GREY_B, Line, RED, UP, VGroup, VMobject, YELLOW


PROP_STROKE_WIDTH = 2.5
FRUIT_HEIGHT = 0.65


def _point(x, y):
    return np.array([x, y, 0.0])


def _closed_curve(start, segments, color, stroke_width):
    curve = VMobject(
        stroke_color=color, stroke_width=stroke_width, fill_opacity=0,
    )
    curve.start_new_path(_point(*start))
    for handle1, handle2, end in segments:
        curve.add_cubic_bezier_curve_to(
            _point(*handle1), _point(*handle2), _point(*end),
        )
    return curve.close_path()


class AppleOutline(VGroup):
    """A complete apple silhouette and one hollow leaf, without a bite."""

    def __init__(self, height=FRUIT_HEIGHT, color=RED,
                 stroke_width=PROP_STROKE_WIDTH, **kwargs):
        super().__init__(**kwargs)
        self.body = _closed_curve((0, 0.32), [
            ((-0.12, 0.49), (-0.45, 0.52), (-0.51, 0.25)),
            ((-0.59, 0.02), (-0.44, -0.37), (-0.26, -0.49)),
            ((-0.15, -0.55), (-0.10, -0.45), (0, -0.46)),
            ((0.10, -0.45), (0.15, -0.55), (0.26, -0.49)),
            ((0.44, -0.37), (0.59, 0.02), (0.51, 0.25)),
            ((0.45, 0.52), (0.12, 0.49), (0, 0.32)),
        ], color, stroke_width)
        self.leaf = _closed_curve((0.04, 0.43), [
            ((0.07, 0.62), (0.22, 0.75), (0.34, 0.74)),
            ((0.33, 0.57), (0.19, 0.43), (0.04, 0.43)),
        ], color, stroke_width)
        self.add(self.body, self.leaf)
        self.set_height(height).center()


class OrangeOutline(VGroup):
    """A round orange and a short stem; no texture or interior detail."""

    def __init__(self, height=FRUIT_HEIGHT, color=YELLOW,
                 stroke_width=PROP_STROKE_WIDTH, **kwargs):
        super().__init__(**kwargs)
        self.body = Circle(
            radius=0.48, stroke_color=color,
            stroke_width=stroke_width, fill_opacity=0,
        )
        self.stem = Line(
            _point(0, 0.48), _point(0.025, 0.60),
            stroke_color=color, stroke_width=stroke_width,
        )
        self.add(self.body, self.stem)
        self.set_height(height).center()


class SimpleTable(VGroup):
    """Front-view I shape: a wide top, a single support, a narrower foot."""

    def __init__(self, width=3.8, height=1.1, base_width=2.1,
                 color=GREY_B, stroke_width=PROP_STROKE_WIDTH, **kwargs):
        super().__init__(**kwargs)
        style = dict(stroke_color=color, stroke_width=stroke_width)
        self.top = Line(_point(-width / 2, height / 2),
                        _point(width / 2, height / 2), **style)
        self.support = Line(_point(0, height / 2),
                            _point(0, -height / 2), **style)
        self.foot = Line(_point(-base_width / 2, -height / 2),
                         _point(base_width / 2, -height / 2), **style)
        self.add(self.top, self.support, self.foot)


class OpenPlate(VMobject):
    """Three sides of an upward-open trapezoid, with room for two fruits."""

    def __init__(self, width=2.8, base_width=2.2, height=0.5,
                 color=GREY_B, stroke_width=PROP_STROKE_WIDTH, **kwargs):
        super().__init__(stroke_color=color, stroke_width=stroke_width,
                         fill_opacity=0, **kwargs)
        self.set_points_as_corners([
            _point(-width / 2, height), _point(-base_width / 2, 0),
            _point(base_width / 2, 0), _point(width / 2, height),
        ])
        self.center()

    def fruit_positions(self):
        """Return two bottom-alignment anchors that follow plate transforms.

        These are visual positions, not synchronization or capacity state.
        """
        anchors = self.get_points()[::2]
        left, right = anchors[1:3]
        base = right - left
        # A small gap keeps hollow fruit outlines clear of the plate's floor.
        upward = anchors[0] - left + anchors[-1] - right
        return tuple(left + fraction * base + 0.10 * upward
                     for fraction in (0.28, 0.72))


def make_fruit_table():
    """Return table, plate, apple and orange as one reusable Manim group."""
    table = SimpleTable()
    plate = OpenPlate()
    plate.move_to(table.top.get_center() + 0.06 * UP, aligned_edge=-UP)
    apple, orange = AppleOutline(), OrangeOutline()
    for fruit, position in zip((apple, orange), plate.fruit_positions()):
        fruit.move_to(position, aligned_edge=-UP)
    props = VGroup(table, plate, apple, orange)
    props.table, props.plate = table, plate
    props.apple, props.orange = apple, orange
    return props
