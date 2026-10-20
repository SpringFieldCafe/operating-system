"""Render local PNG/GIF previews without requiring FFmpeg."""

from pathlib import Path

from .preview_scene import FamilyMotion, FamilyPortrait


OUTPUT = Path(__file__).resolve().parent / "preview"


class _CaptureMotion(FamilyMotion):
    def emit_frame(self):
        self.frames.append(self.get_image().convert("RGB"))


def main():
    OUTPUT.mkdir(exist_ok=True)
    camera = {"resolution": (1280, 720), "fps": 24}
    portrait = FamilyPortrait(camera_config=camera)
    portrait.run()
    # A static Scene has no play()/wait() to trigger a camera draw.
    portrait.update_frame(force_draw=True)
    portrait.get_image().save(OUTPUT / "family.png")

    motion = _CaptureMotion(camera_config=camera)
    motion.frames = []
    motion.run()
    motion.frames[0].save(
        OUTPUT / "family_motion.gif",
        save_all=True,
        append_images=motion.frames[1:],
        duration=1000 / camera["fps"],
        loop=0,
        disposal=2,
    )
    print(f"Rendered family.png and family_motion.gif ({len(motion.frames)} frames).")


if __name__ == "__main__":
    main()
