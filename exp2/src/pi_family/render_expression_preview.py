"""Render the role-state preview and retain stills for visual inspection."""

from pathlib import Path
from PIL import Image

from .preview_scene import FamilyExpressionDemo


OUTPUT = Path(__file__).resolve().parent / "preview"


class CaptureExpressions(FamilyExpressionDemo):
    reaction_seed = 12

    def emit_frame(self):
        self.frames.append(self.get_image().convert("RGB"))


def main():
    OUTPUT.mkdir(exist_ok=True)
    scene = CaptureExpressions(camera_config={"resolution": (960, 540), "fps": 30})
    scene.frames = []
    scene.run()
    for name, seconds in (("ready", 0.8), ("son_first", 7.5), ("daughter_first", 11), ("parent_wait", 13), ("son_second", 16.5), ("daughter_second", 20.2), ("all_wait", 22.2)):
        scene.frames[min(round(seconds * 30), len(scene.frames) - 1)].save(OUTPUT / f"expression_{name}.png")
    # Build the palette from multiple states, so captions and mouth shapes
    # introduced later are retained instead of disappearing into a first-frame palette.
    samples = [frame.resize((240, 135)) for frame in scene.frames[::30]]
    atlas = Image.new("RGB", (240, 135 * len(samples)))
    for index, sample in enumerate(samples):
        atlas.paste(sample, (0, 135 * index))
    palette = atlas.quantize(colors=256)
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in scene.frames]
    durations = [40 if index % 3 == 1 else 30 for index in range(len(frames))]
    frames[0].save(OUTPUT / "family_expressions.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=2, optimize=False)
    print(f"Rendered {len(scene.frames)} frames ({len(scene.frames) / 30:.2f}s), seed {scene.reaction_seed}.")
    for actor in scene.behavior.reactions:
        print(type(actor.pi).__name__, "states:", actor.events)
    return scene


if __name__ == "__main__":
    main()
