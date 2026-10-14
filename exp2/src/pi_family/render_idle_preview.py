"""Render a repeatable preview of independent idle faces with the saved gesture."""

from pathlib import Path
from PIL import Image

from .preview_scene import FamilyIdleDemo


OUTPUT = Path(__file__).resolve().parent / "preview"


class CaptureIdle(FamilyIdleDemo):
    idle_seed = 42

    def emit_frame(self):
        self.frames.append(self.get_image().convert("RGB"))


def main():
    OUTPUT.mkdir(exist_ok=True)
    scene = CaptureIdle(camera_config={"resolution": (960, 540), "fps": 30})
    scene.frames = []
    scene.run()
    scene.frames[0].save(OUTPUT / "idle_start.png")
    scene.frames[150].save(OUTPUT / "idle_with_hand.png")
    palette = scene.frames[0].quantize(colors=256)
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in scene.frames]
    durations = [40 if index % 3 == 1 else 30 for index in range(len(frames))]
    frames[0].save(
        OUTPUT / "family_idle.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(f"Rendered independent gaze/blink preview ({len(scene.frames)} frames, seed 42).")
    for controller in scene.idle.controllers:
        print(controller.role, "blink times:", [round(time, 2) for time in controller.blink_events])
    return scene


if __name__ == "__main__":
    main()
