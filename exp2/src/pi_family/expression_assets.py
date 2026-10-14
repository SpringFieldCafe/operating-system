"""Fetch the two public reference SVGs into an untracked local asset cache."""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
import xml.etree.ElementTree as ET


REFERENCE = Path(__file__).resolve().parent / "assets" / "reference"
COMMIT = "6a5babc6518d7d7e604c503db98abdbb269d087e"
BASE_URL = f"https://raw.githubusercontent.com/CaftBotti/manim_pi_creatures/{COMMIT}/PiCreature"
HASHES = {
    "happy": "bf4f55a7ad22b710317672db13436cc2da3f99d66b9367f8817768cfe80e6ecd",
    "hooray": "eb0553be9a962a8f8db910f3057ad3e7d824c4066e22c7b6d9dba3d973be5bf7",
}


def reference_path(mode):
    if mode not in ("happy", "hooray"):
        raise ValueError("Only happy and hooray are reference poses.")
    path = REFERENCE / f"PiCreatures_{mode}.svg"
    if not path.is_file():
        raise FileNotFoundError("Run python pi_family/expression_assets.py to fetch the reference SVGs.")
    if sha256(path.read_bytes()).hexdigest() != HASHES[mode]:
        raise ValueError(f"Reference SVG checksum mismatch: {mode}")
    return path


def main():
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for mode in ("happy", "hooray"):
        name = f"PiCreatures_{mode}.svg"
        with urlopen(f"{BASE_URL}/{name}", timeout=30) as response:
            data = response.read(32_768)
        root = ET.fromstring(data)
        if len(list(root.iter("{http://www.w3.org/2000/svg}path"))) != 6:
            raise ValueError("Expected the public six-part PiCreature SVG.")
        if sha256(data).hexdigest() != HASHES[mode]:
            raise ValueError(f"Reference SVG checksum mismatch: {mode}")
        (REFERENCE / name).write_bytes(data)
        print(f"{name}: SHA-256 {sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
