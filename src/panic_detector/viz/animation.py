"""Stream a sampled historical replay to GIF or MP4 outside the GUI thread."""

from pathlib import Path
import shutil

# FFmpeg runs locally with a fixed argument list.
import subprocess  # nosec B404
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from panic_detector.data.sectors import SECTOR_COLORS, SECTOR_MAP
from panic_detector.models.panic_score import classify_status
from panic_detector.viz.plots import Scene
from panic_detector.viz.theme import COLORS
from panic_detector.service import atomic_target


def frame(scene: Scene, index: int) -> Image.Image:
    row = scene.rows[index]
    state = classify_status(row["level"])
    img = Image.new("RGB", (768, 384), COLORS["background"])
    d = ImageDraw.Draw(img)
    for text, xy, size, color in [
        ("Market Mood", (24, 24), 22, COLORS["text"]),
        (row["date"], (24, 76), 18, COLORS["muted"]),
        (state, (24, 120), 48, COLORS[state.lower()]),
        (f"Panic level   {row['level']:.1f} / 100", (24, 200), 21, COLORS["text"]),
    ]:
        d.text(xy, text, font=ImageFont.load_default(size=size), fill=color)
    xy = scene.positions[index] * [145, -145] + [555, 190]
    for edge_group in scene.lines[index]:
        for a, b in edge_group.T.reshape(-1, 2, 2) * [145, -145] + [555, 190]:
            d.line([tuple(a), tuple(b)], fill="#334543")
    for (x, y), symbol in zip(xy, scene.symbols):
        d.ellipse(
            (x - 3, y - 3, x + 3, y + 3),
            fill=SECTOR_COLORS.get(SECTOR_MAP.get(symbol, ""), "#aaaaaa"),
        )
    return img


def export_animation(scene: Scene, target: Path) -> None:
    indices = np.linspace(0, len(scene.rows) - 1, min(120, len(scene.rows)), dtype=int)
    with atomic_target(target) as tmp:
        images = (frame(scene, i) for i in indices)
        if target.suffix.lower() == ".gif":
            next(images).save(tmp, save_all=True, append_images=images, loop=0, duration=100)
            return
        encoder = shutil.which("ffmpeg")
        if not encoder:
            raise ValueError("Install FFmpeg and try exporting the MP4 again.")
        with subprocess.Popen(  # nosec B603
            [
                encoder,
                "-loglevel",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                "768x384",
                "-r",
                "10",
                "-i",
                "pipe:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(tmp),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ) as process:
            if process.stdin is None:
                raise ValueError("Reinstall FFmpeg and try exporting again.")
            for img in images:
                process.stdin.write(img.tobytes())
            process.stdin.close()
            if process.wait():
                raise ValueError("Check that FFmpeg supports H.264 and try again.")
