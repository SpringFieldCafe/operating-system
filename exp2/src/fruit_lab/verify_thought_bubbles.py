"""Render thought clouds and check bounds, motion, clearance and lifecycle."""

import argparse
from itertools import combinations
from pathlib import Path
import sys


OUTPUT = Path(__file__).resolve().parents[3] / ".privacy-review" / "thought-clouds"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    sys.argv[:] = [sys.argv[0]]
    import numpy as np
    from manimlib import Intersection
    from pi_family import WalkTo
    from pi_family.contact_layout import sample_contour
    from .scene import FruitLabScene
    from .thought_bubbles import (THOUGHT_DIRECTIONS, THOUGHT_PHASE_SPEEDS, ThoughtCloud,
                                  assign_cloud_variants, cloud_outline)
    from .visuals import WAIT_WORDS, text

    scene = FruitLabScene(camera_config={"fps": 30})
    frames = []
    closeups = []
    try:
        scene.build_lab()
        lab, view = scene.lab, scene.lab.presentation
        assert scene.camera.default_pixel_shape == (1440, 810)
        assert np.allclose([scene.frame.get_width(), scene.frame.get_height()], [18, 10.125])
        assert 1440 / scene.frame.get_width() == 1280 / 16
        bodies = {key: pi.body.get_points().copy() for key, pi in view.actors.items()}
        props = view.props.table.get_all_points().copy()
        if args.render:
            OUTPUT.mkdir(parents=True, exist_ok=True)

        def tick(dt=1 / 30):
            # Visual stress samples are independent of process scheduling.
            lab.business_time += dt
            lab.ambient_time += dt
            view.tick(dt)

        def save(name):
            if args.render:
                scene.camera.capture(*scene.mobjects)
                scene.get_image().save(OUTPUT / name)

        def bounds(mob):
            points = mob.get_all_points()
            return points[:, :2].min(axis=0), points[:, :2].max(axis=0)

        def separated(a, b, margin=0.025):
            low_a, high_a = bounds(a)
            low_b, high_b = bounds(b)
            return np.any(high_a + margin < low_b) or np.any(high_b + margin < low_a)

        def clears_body(cloud, body):
            if separated(cloud, body):
                return True
            # A Pi's arms are above its feet: a full bounding rectangle can
            # overlap a lower cloud even though the actual silhouette clears it.
            low, high = bounds(cloud)
            contour = sample_contour(body, 17)[:, :2]
            if not np.any(np.all((contour > low - 0.025) & (contour < high + 0.025), axis=1)):
                return True
            # Use the actual filled curves when their boxes touch: an arm can
            # sit below the cloud's outer lobe while clearing its real contour.
            return not len(Intersection(cloud, body).get_all_points())

        def check_layout():
            for key, bubble in view.bubbles.items():
                assert len(bubble.body) == 2, "Exactly one main and one detached cloud"
                assert np.sign(bubble.cloud.get_x() - view.heads[key][0]) == np.sign(view.homes[key][0]), (key, "cloud must face outward")
                low, high = bounds(bubble)
                assert np.all(low > [-8.9, -4.9625]) and np.all(high < [8.9, 4.9625]), (key, low, high)
                text_low, text_high = bounds(bubble.content)
                cloud_low, cloud_high = bounds(bubble.cloud)
                assert np.all(text_low > cloud_low + 0.12) and np.all(text_high < cloud_high - 0.12)
                assert clears_body(bubble.cloud, bubble.connector), (key, "small cloud touches main cloud")
                assert separated(bubble.connector, view.actors[key].eyes), (key, "small cloud touches eyes")
                if hasattr(view.actors[key], "eyelashes"):
                    assert separated(bubble.connector, view.actors[key].eyelashes), (key, "small cloud touches eyelashes")
                for actor_key, pi in view.actors.items():
                    assert clears_body(bubble.cloud, pi.body), (key, actor_key, "body")
                    for label in view.labels[actor_key]:
                        assert separated(bubble.cloud, label), (key, actor_key, "label")
                for hud in (view.title, view.run_label, view.caption, view.props.table, view.props.plate):
                    assert separated(bubble.cloud, hud), (key, "HUD/props")
            for (key_a, a), (key_b, b) in combinations(view.bubbles.items(), 2):
                assert separated(a, b, 0.12), (key_a, key_b, "cloud overlap")
            for child, parent in (("son", "mother"), ("daughter", "father")):
                if child in view.bubbles:
                    _, child_high = bounds(view.bubbles[child].cloud)
                    parent_low, _ = bounds(view.labels[parent][1])
                    assert parent_low[1] - child_high[1] > 0.35, (child, parent, "row gap")

        # Distinct file names alone are insufficient: measure the actual static
        # silhouettes after sizing/softening, independently of motion phases.
        pairings = set()
        for seed in range(100):
            assignment = assign_cloud_variants(view.actors, seed=seed)
            assert assignment == assign_cloud_variants(view.actors, seed=seed)
            assert all({pair[i] for pair in assignment.values()} == set(range(4)) for i in (0, 1))
            pairings.update(assignment.values())
        assert len(pairings) == 16, "Main and connector shuffles are coupled"
        angles = np.linspace(-np.pi, np.pi, 720, endpoint=False)
        minimum_differences = {}
        for kind, width, minimum_pixels in (("main", 1.9975, 3.0), ("connector", 0.345, 0.8)):
            profiles = []
            ratios = []
            for variant in range(4):
                outline = cloud_outline(width, kind=kind, variant=variant)
                contour = sample_contour(outline, 17) - outline.get_center()
                polar = np.arctan2(contour[:, 1], contour[:, 0])
                radius = np.linalg.norm(contour[:, :2], axis=1)
                order = np.argsort(polar)
                profiles.append(np.interp(angles, polar[order], radius[order], period=2 * np.pi))
                ratios.append(outline.get_height() / outline.get_width())
            assert np.ptp(ratios) < 0.001, (kind, "aspect envelope changed")
            differences = [80 * np.max(np.abs(a - b)) for a, b in combinations(profiles, 2)]
            assert min(differences) > minimum_pixels, (kind, "silhouettes too similar", differences)
            minimum_differences[kind] = round(min(differences), 3)

        samples = 0
        # Every role sees all 16 main/connector combinations with every caption.
        # This also checks each silhouette at several moving-wave states.
        for reason in WAIT_WORDS:
            content = text(WAIT_WORDS[reason], 23).set_max_width(2.9)
            for main_shift in range(4):
                for connector_shift in range(4):
                    view.bubbles = {key: ThoughtCloud(
                        content.copy(), view.heads[key], THOUGHT_DIRECTIONS[key],
                        child=key in ("son", "daughter"), seed=31 + index,
                        phase_speeds=THOUGHT_PHASE_SPEEDS[key],
                        shape_variants=((index + main_shift) % 4, (index + connector_shift) % 4))
                        for index, key in enumerate(view.actors)}
                    for elapsed in (0, 0.4, 0.9, 1.5, 2.4):
                        for bubble in view.bubbles.values():
                            bubble.update_motion(elapsed)
                        check_layout()
                        samples += 1
        view.bubbles = {}

        for reason in WAIT_WORDS:
            for key in view.actors:
                view.waiting(key, reason)
            for i in range(90):
                tick()
                if reason == "space" and i in (5, 20, 45):
                    save(f"entrance_{i:02d}.png")
            assert all(b.entrance_track.done for b in view.bubbles.values())
            assert all(len({b.shape_variants[i] for b in view.bubbles.values()}) == 4 for i in (0, 1))
            seeds = [seed for bubble in view.bubbles.values() for seed in bubble.motion_seeds]
            motions = [motion for bubble in view.bubbles.values()
                       for motion in (bubble._main_motion, bubble._connector_motion)]
            assert len(set(seeds)) == 8, "Clouds share random seeds"
            assert len({motion.phase for motion in motions}) == 8, "Clouds share initial phases"
            assert len({abs(motion.phase_speed) for motion in motions}) == 8, "Clouds share wave speeds"
            assert all(2 <= abs(motion.phase_speed) <= 3 for motion in motions), "Wave speed outside 2t–3t range"
            signatures = [[] for _ in range(8)]
            if reason == "space":
                save("reference_clouds.png")
                save("outward_clouds.png")
                save("centered_connectors.png")
                save("variant_clouds.png")
            original = {k: b for k, b in view.bubbles.items()}
            for key in view.actors:
                view.waiting(key, reason)
                assert view.bubbles[key] is original[key], "Repeated reason restarted the bubble"
            before = {key: b.cloud.get_points().copy() for key, b in view.bubbles.items()}
            shapes = {key: (b.cloud.get_points() - b.cloud.get_center(),
                            b.connector.get_points() - b.connector.get_center())
                      for key, b in view.bubbles.items()}
            previous = {key: (b.cloud.get_points().copy(), b.connector.get_points().copy())
                        for key, b in view.bubbles.items()}
            excursions = {key: np.zeros(2) for key in view.bubbles}
            glyphs = {key: b.content.get_all_points() - b.content.get_center() for key, b in view.bubbles.items()}
            text_anchors = {key: b.content.get_all_points().copy() for key, b in view.bubbles.items()}
            # Sample multiple cycles, including simultaneous maximum excursions.
            for i in range(240):
                tick(1 / 15)
                check_layout()
                samples += 1
                for index, bubble in enumerate(view.bubbles.values()):
                    elapsed = lab.ambient_time - bubble._motion_start
                    for offset, motion in enumerate((bubble._main_motion, bubble._connector_motion)):
                        signatures[2 * index + offset].append(motion.wave_at(0.0, elapsed))
                for key, bubble in view.bubbles.items():
                    glyph_error = np.max(np.abs(bubble.content.get_all_points() - bubble.content.get_center() - glyphs[key]))
                    assert glyph_error < 2e-6, (key, "glyph drift", glyph_error)
                    assert np.array_equal(bubble.content.get_all_points(), text_anchors[key]), (key, "text anchor moved")
                    assert np.max(np.linalg.norm(bubble.cloud.get_points() - before[key], axis=1)) < 0.13
                    for index, part in enumerate((bubble.cloud, bubble.connector)):
                        points = part.get_points()
                        assert np.max(np.linalg.norm(points - previous[key][index], axis=1)) < 0.015, (key, "motion jump")
                        excursions[key][index] = max(excursions[key][index], np.max(np.linalg.norm(
                            points - part.get_center() - shapes[key][index], axis=1)))
                    previous[key] = (bubble.cloud.get_points().copy(), bubble.connector.get_points().copy())
                if args.render and reason == "space" and i < 120:
                    scene.camera.capture(*scene.mobjects)
                    rendered = scene.get_image().convert("RGB")
                    frames.append(rendered.resize((960, 540)))
                    closeups.append(rendered.crop((1060, 0, 1340, 180)).resize((840, 540)))
            assert all(not np.array_equal(before[k], b.cloud.get_points()) for k, b in view.bubbles.items())
            assert all(main > 0.01 and small > 0.005 for main, small in excursions.values()), excursions
            for first, second in combinations(signatures, 2):
                assert not np.allclose(first, second, atol=1e-4), "Cloud rhythms are synchronized"
            save(f"four_clouds_{reason}.png")

        # Pausing business must leave both cloud outlines moving on ambient time.
        paused = {key: b.get_all_points().copy() for key, b in view.bubbles.items()}
        paused_shapes = {key: (b.cloud.get_points() - b.cloud.get_center(),
                               b.connector.get_points() - b.connector.get_center())
                         for key, b in view.bubbles.items()}
        business_time = lab.business_time
        for _ in range(90):
            lab.ambient_time += 1 / 30
            view.tick(0)
            check_layout()
            samples += 1
        assert lab.business_time == business_time
        assert all(not np.array_equal(paused[k], b.get_all_points()) for k, b in view.bubbles.items())
        for key, bubble in view.bubbles.items():
            for index, part in enumerate((bubble.cloud, bubble.connector)):
                assert not np.allclose(part.get_points() - part.get_center(), paused_shapes[key][index], atol=1e-5)
        assert all(np.array_equal(bodies[k], pi.body.get_points()) for k, pi in view.actors.items())
        assert np.array_equal(props, view.props.table.get_all_points())

        # Recover the traveling phase from actual deformed geometry, rather
        # than merely checking that points change. Each point stays on its
        # original radius while the bulge advances around that radius field.
        phase_checks = 0
        directions = set()
        for variant, (seed, speeds) in enumerate(zip((31, 73, 127, 229), THOUGHT_PHASE_SPEEDS.values())):
            probe = ThoughtCloud(text("等待"), [0, 0, 0], 1, seed=seed, phase_speeds=speeds,
                                 shape_variants=(variant, variant))
            for motion in (probe._main_motion, probe._connector_motion):
                directions.add(np.sign(motion.phase_speed))
                basis = np.column_stack((np.sin(6 * motion.angles),
                                         np.cos(6 * motion.angles), np.ones(len(motion.angles))))
                quarter = np.pi / (2 * abs(motion.phase_speed))
                phases, outlines = [], []
                for elapsed in (0, quarter, 2 * quarter, 4 * quarter):
                    relative = motion.points_at(elapsed) - motion.center
                    cross = relative[:, 0] * motion.relative[:, 1] - relative[:, 1] * motion.relative[:, 0]
                    assert np.max(np.abs(cross)) < 2e-6, "The whole contour rotated"
                    stretch = (np.sum(relative * motion.relative, axis=1)
                               / np.sum(motion.relative**2, axis=1) - 1)
                    assert np.max(np.abs(stretch)) <= motion.amplitude + 2e-6
                    coefficients = np.linalg.lstsq(basis, stretch, rcond=None)[0]
                    assert abs(np.linalg.norm(coefficients[:2]) - motion.amplitude) < 2e-6
                    assert np.max(np.abs(stretch - basis @ coefficients)) < 2e-6, "Contour contains extra deformation/noise"
                    phases.append(np.arctan2(coefficients[1], coefficients[0]))
                    outlines.append(relative)
                for index in (1, 2):
                    expected = np.sign(motion.phase_speed) * index * np.pi / 2
                    error = np.angle(np.exp(1j * (phases[index] - phases[0] - expected)))
                    assert abs(error) < 2e-4, "Bulges do not travel in the selected direction"
                assert np.allclose(outlines[0], outlines[-1], atol=2e-6), "Pure sine wave does not repeat after its period"
                phase_checks += 1
        assert directions == {-1, 1}, "Diagnostic clouds do not exercise both travel directions"

        # Reproducible diagnostic seeds; separate seeds produce different shape
        # motion, and equal elapsed times give the same state at different FPS.
        probes = [ThoughtCloud(text("等待"), [0, 0, 0], 1, seed=seed) for seed in (7, 7, 29)]
        for probe in probes:
            probe.update_motion(0)
        for elapsed in np.linspace(0, 12, 361):
            probes[0].update_motion(elapsed)
            probes[2].update_motion(elapsed)
        for elapsed in np.linspace(0, 12, 121):
            probes[1].update_motion(elapsed)
        for name in ("cloud", "connector"):
            a, b, c = [getattr(probe, name).get_points() for probe in probes]
            assert np.allclose(a, b, atol=1e-6), "Motion depends on FPS"
            assert not np.allclose(a, c, atol=1e-4), "Independent seeds did not change the motion"

        # Walk each existing actor through both original paths with the other
        # three clouds visible; conservative bounds include the swinging arms.
        for key, pi in view.actors.items():
            bubble = view.bubbles.pop(key)
            for destination in (view.contacts[key], view.homes[key]):
                walk = WalkTo(pi, destination, run_time=1.9)
                walk.begin()
                for alpha in np.linspace(0, 1, 121):
                    walk.interpolate(alpha)
                    pi.refresh_bounding_box(recurse_down=True)
                    check_layout()
                    samples += 1
                walk.finish()
            view.bubbles[key] = bubble

        # Clear during an entrance, and replace the reason before it completes.
        for key in view.actors:
            view.clear_bubble(key)
        for _ in range(40):
            tick()
        assert not view.bubbles and not view.effects
        for _ in range(3):
            previous_assignment = view.cloud_variants
            for key in view.actors:
                view.waiting(key, "space")
            assert view.cloud_variants is not previous_assignment, "A fresh group did not reshuffle"
            assignment = view.cloud_variants
            tick(0.2)
            for key in view.actors:
                view.waiting(key, "mutex")
            assert view.cloud_variants is assignment, "Replacement reshuffled a visible group"
            assert all(b.shape_variants == assignment[key] for key, b in view.bubbles.items())
            tick(0.2)
            removed = list(view.bubbles.values())
            for key in view.actors:
                view.clear_bubble(key)
            for _ in range(40):
                tick()
            assert not view.bubbles and not view.effects
            family = scene.get_mobject_family_members()
            assert all(b not in family and b.content not in family for b in removed)

        # A pause during Write must not freeze a half-drawn thought cloud.
        for key in view.actors:
            view.waiting(key, "space")
        tick(0.2)
        business_time = lab.business_time
        for _ in range(90):
            lab.ambient_time += 1 / 30
            view.tick(0)
        assert lab.business_time == business_time
        assert all(b.entrance_track.done for b in view.bubbles.values())
        for key in view.actors:
            view.clear_bubble(key)
        for _ in range(40):
            lab.ambient_time += 1 / 30
            view.tick(0)
        assert not view.bubbles and not view.effects

        if args.render and frames:
            # GIF timing is quantized to 10 ms; this pattern preserves 15 FPS.
            durations = [60 if index % 3 == 1 else 70 for index in range(len(frames))]
            frames[0].save(OUTPUT / "variant_clouds.gif", save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, disposal=2)
            closeups[0].save(OUTPUT / "variant_clouds_closeup.gif", save_all=True, append_images=closeups[1:],
                             duration=durations, loop=0, disposal=2)
        print(f"THOUGHT_CLOUDS_OK samples={samples}; phase_checks={phase_checks}; variant_min_difference_px={minimum_differences}; 4+4 silhouettes; independent nonrepeating shuffles; all role/caption/shape combinations; fade reservations; outward clouds; row gap >28px; eight independent seeds/phases/speeds; pure sine; fixed anchors; bounds; glyphs; ambient pause; walk clearance; interrupted cleanup", flush=True)
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
