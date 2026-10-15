"""One left-hand placement gesture using the author's SVG/change/play workflow."""

from manimlib import smooth
from math import isfinite

from .upstream.pi_creature import PiCreature
from .hand_poses import source_hand
from .carrying import carry_fruit


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
    for pi in characters:
        pi._active_hand = "right" if pi.is_flipped() else "left"
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


def take_left_hand(scene, characters, run_time=1.8):
    """Reach to the take position, lift gently, then return before celebrating."""
    if run_time <= 0:
        raise ValueError("run_time must be positive.")
    characters = (characters,) if isinstance(characters, PiCreature) else tuple(characters)
    if not characters:
        raise ValueError("At least one character is required.")
    for pi in characters:
        pi._active_hand = "right" if pi.is_flipped() else "left"
    scene.play(*[pi.change("left_hand_place") for pi in characters], run_time=0.35 * run_time, rate_func=smooth)
    scene.wait(0.12 * run_time)
    scene.play(*[pi.change("left_hand_reach") for pi in characters], run_time=0.18 * run_time, rate_func=smooth)
    scene.play(*[pi.change("plain") for pi in characters], run_time=0.35 * run_time, rate_func=smooth)


def _prepare(characters, hand, run_time, fruit):
    if not isfinite(run_time) or run_time <= 0:
        raise ValueError("run_time must be finite and positive.")
    characters = (characters,) if isinstance(characters, PiCreature) else tuple(characters)
    if not characters or (fruit is not None and len(characters) != 1):
        raise ValueError("Choose at least one actor; one fruit requires one actor.")
    modes = []
    for pi in characters:
        if getattr(pi, "_body_reaction_active", False):
            raise ValueError("Finish the celebration before a hand gesture.")
        side = source_hand(pi, hand)
        attachment = getattr(pi, "_fruit_attachment", None)
        if attachment is not None and attachment.hand != hand:
            raise ValueError("Use the hand currently holding the fruit.")
        if attachment is not None and fruit is not None and attachment.fruit is not fruit:
            raise ValueError("This actor is holding a different fruit.")
        pi._active_hand = hand
        modes.append(side)
    return characters, modes


def place_hand(scene, characters, hand="left", run_time=2.0, fruit=None):
    """Use a screen-side hand; release its held fruit at the placement pose."""
    characters, sides = _prepare(characters, hand, run_time, fruit)
    if fruit is not None and getattr(characters[0], "_fruit_attachment", None) is None:
        raise ValueError("Attach the carried fruit before placing it.")
    def phase(name, fraction):
        scene.play(*[pi.change(f"{side}_hand_{name}") for pi, side in zip(characters, sides)],
                   run_time=fraction*run_time, rate_func=smooth)
    phase("reach", 0.32)
    phase("place", 0.21)
    for pi in characters:
        attachment = getattr(pi, "_fruit_attachment", None)
        if attachment is not None:
            attachment.release()
    scene.wait(0.12*run_time)
    scene.play(*[pi.change("plain") for pi in characters], run_time=0.35*run_time, rate_func=smooth)


def take_hand(scene, characters, hand="left", run_time=1.8, fruit=None):
    """Attach the fruit without a jump at contact, then lift and withdraw."""
    characters, sides = _prepare(characters, hand, run_time, fruit)
    if fruit is not None and getattr(characters[0], "_fruit_attachment", None) is not None:
        raise ValueError("Release the held fruit before taking another one.")
    scene.play(*[pi.change(f"{side}_hand_place") for pi, side in zip(characters, sides)],
               run_time=0.35*run_time, rate_func=smooth)
    if fruit is not None:
        carry_fruit(characters[0], fruit, hand=hand, snap=False)
    scene.wait(0.12*run_time)
    scene.play(*[pi.change(f"{side}_hand_reach") for pi, side in zip(characters, sides)],
               run_time=0.18*run_time, rate_func=smooth)
    scene.play(*[pi.change(f"{side}_hand_hold" if fruit is not None else "plain")
                 for pi, side in zip(characters, sides)], run_time=0.35*run_time, rate_func=smooth)


def place_right_hand(scene, characters, run_time=2.0):
    return place_hand(scene, characters, hand="right", run_time=run_time)


def take_right_hand(scene, characters, run_time=1.8):
    return take_hand(scene, characters, hand="right", run_time=run_time)
