"""Build the Windows x64 game folder and ZIP with PyInstaller.

Run from a clean Python 3.13 environment on Windows:

    python -m pip install . pygame-ce==2.5.8 pyinstaller==6.22.3
    python packaging/windows/build.py
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUNDLED_DOCS = ("LICENSE", "MAP_SOURCES.md", "THIRD_PARTY.md", "MUSIC_CREDITS.md")
# Authoring-only libraries that must not be pulled into the executable.
EXCLUDED = ("numpy", "shapely", "PIL", "tkinter")
SMOKE_TIMEOUT = 60


def freeze(output: Path, work: Path) -> Path:
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed",
        "--name", "CARS", "--icon", str(HERE / "cars.ico"), "--collect-data", "cars",
        "--distpath", str(output), "--workpath", str(work / "cache"), "--specpath", str(work),
    ]  # fmt: skip
    for module in EXCLUDED:
        command += ["--exclude-module", module]
    subprocess.run([*command, str(HERE / "launcher.py")], cwd=ROOT, check=True)
    return output / "CARS"


def add_notices(target: Path) -> None:
    for name in BUNDLED_DOCS:
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(HERE / "PLAY.txt", target / "PLAY.txt")
    shutil.copytree(HERE / "licenses", target / "licenses", dirs_exist_ok=True)
    shutil.copytree(ROOT / "examples", target / "examples", dirs_exist_ok=True)


def smoke_test(target: Path) -> None:
    executable = str(target / "CARS.exe")
    for extra in ([], ["--tutorial"], ["--replay", str(target / "examples" / "opening.json")]):
        subprocess.run([executable, "--smoke", *extra], cwd=target.parent, check=True, timeout=SMOKE_TIMEOUT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Build the Windows download on Windows; other platforms run from source.")
    output = args.output.resolve()
    # Start clean so files removed from the project never linger in the download.
    shutil.rmtree(output / "CARS", ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    target = freeze(output, ROOT / "build" / "windows")
    add_notices(target)
    smoke_test(target)
    archive = shutil.make_archive(str(output / "CARS-Windows"), "zip", output, "CARS")
    print("Download:", archive)


if __name__ == "__main__":
    main()
