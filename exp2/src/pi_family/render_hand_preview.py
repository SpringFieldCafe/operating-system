"""Render the one hand gesture as a local GIF without FFmpeg."""

from pathlib import Path
from PIL import Image

from .preview_scene import LeftHandPlacementDemo


OUTPUT = Path(__file__).resolve().parent / "preview"


class CapturePlacement(LeftHandPlacementDemo):
    def emit_frame(self):
        frame = self.get_image().convert("RGB")
        self.frames.append(frame)
        if 1.6 <= self.time <= 1.7:
            self.placed_frame = frame.copy()


def main():
    OUTPUT.mkdir(exist_ok=True)
    scene = CapturePlacement(camera_config={"resolution": (1280, 720), "fps": 30})
    scene.frames, scene.placed_frame = [], None
    scene.run()
    scene.frames[0].save(OUTPUT / "hand_start.png")
    if scene.placed_frame is None:
        raise RuntimeError("The placement pause was not rendered.")
    scene.placed_frame.save(OUTPUT / "hand_place.png")
    # Use one palette for the entire GIF so static pixels keep the same colors.
    palette = scene.frames[0].quantize(colors=256)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in scene.frames]
    gif_frames[0].save(
        OUTPUT / "left_hand_placement.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=1000 / 30,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(f"Rendered one left-hand placement gesture ({len(scene.frames)} frames).")
    return scene


if __name__ == "__main__":
    main()
