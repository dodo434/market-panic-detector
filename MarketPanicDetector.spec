# Build each OS on its native runner. Bundle only the public application configuration.
from pathlib import PurePosixPath

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[("configs/app.yaml", "mood_configs")],
    hiddenimports=["mood_configs", "keyring.backends.SecretService", "keyring.backends.Windows"],
    excludes=[
        "matplotlib",
        "tkinter",
        "notebook",
        "IPython",
        "numba",
        "llvmlite",
        "sklearn",
        "torch",
        "tensorflow",
        "pytest",
        "scipy.tests",
        "pandas.tests",
        "pyarrow.tests",
        "cv2",
        "PyQt5",
        "PyQt6",
        "backend",
        "yfinance",
        "fastapi",
    ],
    hooksconfig={"matplotlib": {"backends": []}},
)


def runtime_data(name):
    path = PurePosixPath(name.replace("\\", "/"))
    if "tests" in path.parts:
        return False
    if path.parts[0] == "pyarrow":
        return "include" not in path.parts and path.suffix not in {
            ".pyx",
            ".pxd",
            ".pxi",
            ".h",
            ".hpp",
        }
    return True


a.datas = [item for item in a.datas if runtime_data(item[0])]
for name, source, kind in a.datas + a.binaries:
    path = PurePosixPath(name.replace("\\", "/"))
    if (
        path.is_absolute()
        or ".." in path.parts
        or (path.name.lower().startswith(".env") or path.name.lower() == "api.txt")
        or (
            path.suffix.lower() in {".pem", ".key", ".parquet", ".npy"}
            and path.as_posix() != "certifi/cacert.pem"
            and path.parts[0] not in {"numpy", "scipy"}
        )
    ):
        raise ValueError("Unexpected private data or absolute archive member")
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MarketMood",
    debug=False,
    icon="src/panic_detector/app/market-mood.ico",
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MarketMood")
