"""Export four comparable contact poses using the actual ManimGL renderer."""

from .props_scene import (
    DaughterContactPreview, FatherContactPreview,
    MotherContactPreview, SonContactPreview,
)
from .render_props_preview import OUTPUT


def main():
    OUTPUT.mkdir(exist_ok=True)
    for scene_type, name in (
        (FatherContactPreview, "father_contact.png"),
        (MotherContactPreview, "mother_contact.png"),
        (SonContactPreview, "son_contact.png"),
        (DaughterContactPreview, "daughter_contact.png"),
    ):
        scene = scene_type(camera_config={"resolution": (1280, 720)})
        scene.run()
        scene.update_frame(force_draw=True)
        scene.get_image().save(OUTPUT / name)
        print(f"Rendered {name} (1280 x 720).")


if __name__ == "__main__":
    main()
