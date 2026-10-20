"""Render all four roles into a synchronized 2x2 GIF with native ManimGL."""

from pathlib import Path
import gc

from PIL import Image, ImageColor

from .walking_scene import FatherWalkingDemo, MotherWalkingDemo, SonWalkingDemo, DaughterWalkingDemo


OUTPUT = Path(__file__).resolve().parent / "preview"


class _Capture:
    def emit_frame(self):
        self.frames.append(self.get_image().convert("RGB"))

    def mark(self, phase):
        self.marks[phase] = len(self.frames) - 1


def _grid(frames):
    width, height = frames[0].size
    canvas = Image.new("RGB", (width*2, height*2), "#000000")
    for index, frame in enumerate(frames):
        canvas.paste(frame, ((index % 2)*width, (index // 2)*height))
    return canvas


def main():
    OUTPUT.mkdir(exist_ok=True)
    captures, marks = [], []
    for cls in (FatherWalkingDemo, MotherWalkingDemo, SonWalkingDemo, DaughterWalkingDemo):
        capture = type(f"Capture{cls.__name__}", (_Capture, cls), {})
        scene = capture(camera_config={"resolution": (480, 360), "fps": 24})
        scene.frames, scene.marks = [], {}
        scene.run()
        captures.append(scene.frames)
        marks.append(scene.marks)
        print(f"Rendered {cls.role_key}: {len(scene.frames)} frames.")
        scene.behavior.stop()
        attachment = getattr(scene.character, "_fruit_attachment", None)
        if attachment is not None:
            attachment.release()
        del scene
        gc.collect()
    combined = [_grid([frames[min(index, len(frames)-1)] for frames in captures])
                for index in range(max(map(len, captures)))]
    for name in ("start", "arrived", "transferred", "celebrated", "returned"):
        _grid([frames[phase[name]] for frames, phase in zip(captures, marks)]).save(OUTPUT / f"walking_{name}.png")
    combined[33].save(OUTPUT / "walking_midstep.png")
    _grid([frames[min(phase["transferred"] + 17, len(frames)-1)]
           for frames, phase in zip(captures, marks)]).save(OUTPUT / "walking_celebration.png")
    # One palette gathered from the entire sequence, including moving fruit.
    atlas = Image.new("RGB", (480, 360*16))
    for i in range(16):
        atlas.paste(combined[i*(len(combined)-1)//15].resize((480, 360)), (0, i*360))
    adaptive = atlas.quantize(colors=240)
    # Thin hollow outlines occupy few pixels. Reserve their exact colors so
    # palette quantization cannot turn the yellow orange into a dim olive.
    fixed = ("#000000", "#176477", "#B83F49", "#77C9EF", "#F27983", "#FFFF00",
             "#FC6255", "#FFFFFF", "#000000", "#DCA0AD", "#333B48", "#BBBBBB",
             "#FFFF80", "#FF9999", "#888888", "#444444")
    palette = Image.new("P", (1, 1))
    palette.putpalette([value for color in fixed for value in ImageColor.getrgb(color)]
                       + adaptive.getpalette()[:720])
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in combined]
    indexed[0].save(OUTPUT / "family_walking.gif", save_all=True, append_images=indexed[1:],
                    duration=[40 if i % 6 != 5 else 50 for i in range(len(indexed))],
                    loop=0, disposal=2, optimize=False)
    print(f"Saved family_walking.gif: {len(combined)} composite frames.")


if __name__ == "__main__":
    main()
