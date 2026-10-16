"""Build a local coursework source archive using an explicit file allowlist."""

from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    exp = Path(__file__).resolve().parents[2]
    roots = [exp / "src" / "fruit_lab", exp / "src" / "pi_family"]
    files = [exp / name for name in ("README.md", "VERIFICATION.md", "requirements.txt")]
    for base in roots:
        for path in base.rglob("*"):
            relative = path.relative_to(base)
            if not path.is_file() or any(p in ("preview", "__pycache__", "latex_cache") for p in relative.parts):
                continue
            if path.suffix.lower() in (".py", ".md", ".txt", ".svg"):
                files.append(path)
    expected = [exp / "src/pi_family/assets/reference" / f"PiCreatures_{mode}.svg" for mode in ("happy", "hooray", "angry")]
    if any(not path.exists() for path in expected):
        raise RuntimeError("Fetch the three reference assets before packaging: python pi_family/expression_assets.py")
    for path in files:
        if not path.exists():
            raise RuntimeError("Missing source-package input: " + path.name)
    # This checks user-specific path strings without putting the actual home
    # directory or device username into source, logs, or the archive manifest.
    forbidden = {str(Path.home()).encode(), str(Path.home()).replace("\\", "/").encode()}
    manifest = {}
    for path in files:
        data = path.read_bytes()
        if any(value in data for value in forbidden):
            raise RuntimeError("A package input contains a local home path: " + path.name)
        manifest["exp2/" + path.relative_to(exp).as_posix()] = sha256(data).hexdigest()
    output = exp / "report" / "exp2-source.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, "exp2/" + path.relative_to(exp).as_posix())
        archive.writestr("exp2/SOURCE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert all(sha256(archive.read(name)).hexdigest() == value for name, value in manifest.items())
    print(f"Created exp2/report/exp2-source.zip: {len(files)} reviewed source/material files.")


if __name__ == "__main__":
    main()
