"""Check all four roles through the existing placement and take transitions."""

import numpy as np

from .contact_layout import (
    CONTACT_ROLES, hand_contour, make_contact_pose, outer_edges, sample_contour,
)
from .hand_poses import source_geometry, arm_slice


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _point_segment_distance(points, segments):
    a, b = segments[:, 0], segments[:, 1]
    delta = b - a
    lengths = np.sum(delta * delta, axis=1)
    offsets = points[:, None] - a
    alpha = np.sum(offsets * delta, axis=2) / np.maximum(lengths, 1e-20)
    closest = a + np.clip(alpha, 0, 1)[..., None] * delta
    return np.linalg.norm(points[:, None] - closest, axis=2).min()


def _contour_segment_distance(contour, segments):
    """Exact distance between sampled outline edges and straight prop edges."""
    boundary = np.stack((contour[:-1, :2], contour[1:, :2]), axis=1)
    a, r = boundary[:, 0, None], np.diff(boundary, axis=1)[:, 0, None]
    c, s = segments[None, :, 0], np.diff(segments, axis=1)[None, :, 0]
    denominator = _cross(r, s)
    nonparallel = np.abs(denominator) > 1e-12
    divisor = np.where(nonparallel, denominator, 1)
    t, u = _cross(c - a, s) / divisor, _cross(c - a, r) / divisor
    if np.any(nonparallel & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)):
        return 0.0
    return min(
        _point_segment_distance(contour[:, :2], segments),
        _point_segment_distance(segments.reshape(-1, 2), boundary),
    )


def _prop_segments(props):
    lines = [np.array([line.get_start()[:2], line.get_end()[:2]])
             for line in props.table]
    corners = props.plate.get_points()[::2, :2]
    lines.extend(np.stack((corners[:-1], corners[1:]), axis=1))
    return np.array(lines)


def verify_role(role_key):
    role = CONTACT_ROLES[role_key]
    pi, props = make_contact_pose(role_key)
    arm = arm_slice(role.hand)
    props_snapshot = props.get_all_points().copy()
    points = pi.body.get_points()
    fixed = np.concatenate((points[:arm.start], points[arm.stop:]))
    outward = role.side * fixed[:, 0]
    body_gap = outward.min() - props.table.get_width() / 2
    assert body_gap > 0.08, (role_key, "body-table", body_gap)
    assert not pi.is_flipped()
    obstacle_segments = _prop_segments(props)
    fruit_contours = []
    for fruit in (props.apple, props.orange):
        for part in fruit.family_members_with_points():
            contour = sample_contour(part, 51)
            contour[:, 0] *= role.side
            fruit_contours.append(contour)
    initial_hand = hand_contour(pi, 51, side=role.hand)
    contact_gaps = []
    target = getattr(props, role.fruit)
    for part in target.family_members_with_points():
        contour = sample_contour(part, 51)
        contour[:, 0] *= role.side
        edges = outer_edges(contour, initial_hand[:, 1])
        valid = np.isfinite(edges)
        if valid.any():
            contact_gaps.append((role.side * initial_hand[valid, 0] - edges[valid]).min())
    contact_gap = min(contact_gaps)
    assert 0 <= contact_gap < 0.003, (role_key, "missed fruit", contact_gap)
    checked = 0
    prop_gap = float("inf")
    # Cover both real helpers: place goes plain->reach->place->plain;
    # take goes plain->place->reach->plain. Geometry is independent of timing.
    for sequence in (
        ("plain", f"{role.hand}_hand_reach", f"{role.hand}_hand_place", "plain"),
        ("plain", f"{role.hand}_hand_place", f"{role.hand}_hand_reach", "plain"),
    ):
        pi.change_mode(sequence[0])
        for mode in sequence[1:]:
            animation = pi.change(mode).build()
            animation.begin()
            for alpha in np.linspace(0, 1, 31):
                animation.interpolate(float(alpha))
                assert np.isfinite(pi.get_all_points()).all()
                current = pi.body.get_points()
                current_fixed = np.concatenate((current[:arm.start], current[arm.stop:]))
                assert np.array_equal(current_fixed, fixed)
                assert not pi.is_flipped()
                assert np.array_equal(props.get_all_points(), props_snapshot)
                hand = hand_contour(pi, 31, side=role.hand)
                gap = _contour_segment_distance(hand, obstacle_segments)
                prop_gap = min(prop_gap, gap)
                # At the common 1280px/8.2-unit frame, the prop half-stroke
                # is about 0.008 units. Keep additional clearance beyond it.
                assert gap > 0.012, (role_key, mode, alpha, "hand-prop", gap)
                for contour in fruit_contours:
                    edges = outer_edges(contour, hand[:, 1])
                    valid = np.isfinite(edges)
                    if valid.any():
                        clearance = role.side * hand[valid, 0] - edges[valid]
                        assert clearance.min() >= -0.001, (
                            role_key, mode, alpha, "fruit interior", clearance.min(),
                        )
                checked += 1
            animation.finish()
    return body_gap, prop_gap, contact_gap, checked


def main():
    for key in CONTACT_ROLES:
        body_gap, prop_gap, contact_gap, checked = verify_role(key)
        print(f"{key}: body-table {body_gap:.4f}; hand-props {prop_gap:.4f}; "
              f"fruit contact {contact_gap:.4f}; {checked} motion samples passed.")


if __name__ == "__main__":
    main()
