"""Small, reproducible TeX SVG vocabulary, usable without a runtime TeX install."""

from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent / "assets" / "tex"
FORMULAS = {"0": "digit_0", "1": "digit_1", "2": "digit_2", "e=": "empty", "a=": "apple", "o=": "orange",
            **{f"{operation}({symbol})": f"{operation}_{symbol}" for operation in ("P", "V") for symbol in ("e", "a", "o", "m")}}


def build():
    if not shutil.which("latex") or not shutil.which("dvisvgm"):
        raise RuntimeError("Regenerating mathematical assets requires latex and dvisvgm.")
    version = subprocess.run(["latex", "--version"], capture_output=True, timeout=10).stdout
    flags = ["-disable-installer", "--miktex-disable-maintenance"] if b"MiKTeX" in version else []
    ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fruit-lab-tex-") as folder:
        base = Path(folder)
        for formula, filename in FORMULAS.items():
            source = ("\\documentclass{article}\n\\usepackage{amsmath}\n\\pagestyle{empty}\n"
                      "\\begin{document}\\(" + formula + "\\)\\end{document}\n")
            (base / "formula.tex").write_text(source, encoding="utf-8")
            result = subprocess.run(["latex", *flags, "-interaction=nonstopmode", "-halt-on-error", "formula.tex"],
                                    cwd=base, capture_output=True, timeout=30)
            if result.returncode:
                raise RuntimeError("TeX asset compilation failed: " + result.stdout.decode(errors="replace")[-1000:])
            result = subprocess.run(["dvisvgm", "--no-fonts", "--bbox=min", "--stdout", "formula.dvi"],
                                    cwd=base, capture_output=True, timeout=30)
            if result.returncode:
                raise RuntimeError("dvisvgm failed: " + result.stderr.decode(errors="replace")[-1000:])
            svg = result.stdout.decode("utf-8")
            ET.fromstring(svg)
            (ROOT / (filename + ".svg")).write_text(svg, encoding="utf-8")
            print("Compiled TeX:", formula, flush=True)


@lru_cache(maxsize=32)
def _shape(formula, font_size):
    from manimlib import SVGMobject, WHITE
    path = ROOT / (FORMULAS[formula] + ".svg")
    if not path.exists():
        raise RuntimeError("Missing TeX SVG assets. Run: python -m fruit_lab.math_assets")
    height = float(ET.parse(path).getroot().attrib["viewBox"].split()[3])
    zero_height = float(ET.parse(ROOT / "digit_0.svg").getroot().attrib["viewBox"].split()[3])
    return SVGMobject(str(path)).set_color(WHITE).set_height(font_size / 144 * height / zero_height)


def tex(formula, font_size=27):
    return _shape(formula, font_size).copy()


if __name__ == "__main__":
    build()
