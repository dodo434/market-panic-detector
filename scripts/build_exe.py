"""Build the public executable from an explicit spec on the target operating system."""

from pathlib import Path
import PyInstaller.__main__

if __name__ == "__main__":
    spec = Path(__file__).resolve().parents[1] / "MarketPanicDetector.spec"
    PyInstaller.__main__.run(["--clean", "--noconfirm", str(spec)])
