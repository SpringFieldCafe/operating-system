"""Render the real ManimGL waiting/anger/recovery preview and key stills."""

from pathlib import Path
from PIL import Image, ImageColor

from .angry_scene import FamilyAngryDemo


OUTPUT = Path(__file__).resolve().parent / "preview"


class CaptureAngry(FamilyAngryDemo):
    def emit_frame(self):
        self.frames.append(self.get_image().convert("RGB"))

    def mark(self, phase):
        self.marks[phase] = len(self.frames)-1


def main():
    OUTPUT.mkdir(exist_ok=True)
    scene = CaptureAngry(camera_config={"resolution": (1280, 720), "fps": 24})
    scene.frames, scene.marks = [], {}
    scene.run()
    for phase, index in scene.marks.items():
        scene.frames[index].save(OUTPUT / f"angry_{phase}.png")
    samples = [frame.resize((320, 180)) for frame in scene.frames[::12]]
    atlas = Image.new("RGB", (320, 180*len(samples)))
    for index, frame in enumerate(samples):
        atlas.paste(frame, (0, 180*index))
    adaptive = atlas.quantize(colors=248)
    fixed = ("#000000", "#176477", "#B83F49", "#77C9EF", "#F27983", "#FFFFFF", "#000000", "#DCA0AD")
    palette = Image.new("P", (1, 1))
    palette.putpalette([value for color in fixed for value in ImageColor.getrgb(color)]
                       + adaptive.getpalette()[:744])
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in scene.frames]
    frames[0].save(OUTPUT / "family_angry.gif", save_all=True, append_images=frames[1:],
                   duration=[40 if i % 6 != 5 else 50 for i in range(len(frames))],
                   loop=0, disposal=2, optimize=False)
    scene.behavior.stop()
    print(f"Rendered family_angry.gif: {len(frames)} frames at 24fps; marks {scene.marks}.")


if __name__ == "__main__":
    main()
