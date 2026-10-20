"""Save a small real-render wakeup GIF; no FFmpeg or pre-scripted role order."""

from pathlib import Path
import sys
import time


def main():
    sys.argv[:] = [sys.argv[0]]
    from PIL import Image, ImageColor
    from .scene import FruitLabScene
    scene = FruitLabScene(camera_config={"resolution": (960, 540), "fps": 30})
    frames = []
    try:
        scene.build_lab()
        lab = scene.lab
        deadline = time.monotonic() + 20
        while not all(v["pid"] for v in lab.engine.snapshot()["roles"].values()):
            if time.monotonic() > deadline:
                raise RuntimeError("Workers did not start.")
            lab.tick(0)
            time.sleep(0.01)
        lab.batch(father=1, daughter=1)
        deadline = time.monotonic() + 90
        index = 0
        while time.monotonic() < deadline:
            scene.update_frame(1 / 30, force_draw=True)
            if index % 3 == 0:
                frames.append(scene.get_image().convert("RGB").resize((640, 360)))
            index += 1
            snapshot = lab.engine.snapshot()
            if all(snapshot["roles"][r]["completed"] == 1 for r in ("father", "daughter")) and not lab.presentation.tracks:
                break
        else:
            raise AssertionError("Preview workload timed out.")
        output = Path(__file__).resolve().parents[1] / "pi_family" / "preview"
        output.mkdir(exist_ok=True)
        atlas = Image.new("RGB", (640, 360 * 12))
        for i in range(12):
            atlas.paste(frames[i * (len(frames) - 1) // 11], (0, 360 * i))
        adaptive = atlas.quantize(colors=246)
        fixed = ("#000000", "#FFFFFF", "#176477", "#B83F49", "#77C9EF", "#F27983", "#FFFF00", "#FC6255", "#DCA0AD", "#BBBBBB")
        palette = Image.new("P", (1, 1))
        palette.putpalette([v for color in fixed for v in ImageColor.getrgb(color)] + adaptive.getpalette()[:738])
        indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
        indexed[0].save(output / "fruit_lab_wakeup.gif", save_all=True, append_images=indexed[1:], duration=100,
                        loop=0, disposal=2, optimize=False)
        print(f"Rendered fruit_lab_wakeup.gif: {len(frames)} frames, 640x360, 10fps.", flush=True)
    finally:
        if hasattr(scene, "lab"):
            scene.lab.close()


if __name__ == "__main__":
    main()
