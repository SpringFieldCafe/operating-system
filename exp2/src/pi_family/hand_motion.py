"""One left-hand placement gesture using the author's SVG/change/play workflow."""

from manimlib import smooth

from .upstream.pi_creature import PiCreature


def place_left_hand(scene, characters, run_time=2.0):
    """Lift/reach, lower/place, pause, and return; accepts one Pi or a group."""
    if run_time <= 0:
        raise ValueError("run_time must be positive.")
    if isinstance(characters, PiCreature):
        characters = (characters,)
    else:
        characters = tuple(characters)
    if not characters:
        raise ValueError("At least one character is required.")
    scene.play(
        *[pi.change("left_hand_reach") for pi in characters],
        run_time=0.32 * run_time,
        rate_func=smooth,
    )
    scene.play(
        *[pi.change("left_hand_place") for pi in characters],
        run_time=0.21 * run_time,
        rate_func=smooth,
    )
    scene.wait(0.12 * run_time)
    scene.play(
        *[pi.change("plain") for pi in characters],
        run_time=0.35 * run_time,
        rate_func=smooth,
    )
