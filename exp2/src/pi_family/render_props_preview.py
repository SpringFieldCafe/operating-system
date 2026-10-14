"""Render the new props and the four-character layout with ManimGL."""

from pathlib import Path

from .props_scene import FamilyTablePreview, FruitPropsPreview


OUTPUT = Path(__file__).resolve().parent / "preview"


def main():
    OUTPUT.mkdir(exist_ok=True)
    for scene_type, name, resolution in (
        (FruitPropsPreview, "fruit_props.png", (1280, 720)),
        (FamilyTablePreview, "family_table.png", (1280, 720)),
        (FamilyTablePreview, "family_table_small.png", (640, 360)),
    ):
        scene = scene_type(camera_config={"resolution": resolution})
        scene.run()
        scene.update_frame(force_draw=True)
        scene.get_image().save(OUTPUT / name)
        print(f"Rendered {name} ({resolution[0]} x {resolution[1]}).")


if __name__ == "__main__":
    main()
