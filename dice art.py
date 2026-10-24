"""Рисует картинки кубика: шесть граней (PNG), обложку и крутящийся кубик (GIF)."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
PIPS = {
    1: [(0.5, 0.5)],
    2: [(0.27, 0.27), (0.73, 0.73)],
    3: [(0.27, 0.27), (0.5, 0.5), (0.73, 0.73)],
    4: [(0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)],
    5: [(0.27, 0.27), (0.73, 0.27), (0.5, 0.5), (0.27, 0.73), (0.73, 0.73)],
    6: [(0.27, 0.25), (0.73, 0.25), (0.27, 0.5), (0.73, 0.5), (0.27, 0.75), (0.73, 0.75)],
}
BG = (24, 26, 32)


def _die(n: int, angle: float = 0.0, scale: float = 1.0) -> Image.Image:
    """Кубик с тенью на прозрачном фоне, повёрнутый на angle градусов."""
    side = int(SIZE * 0.62 * scale)
    die = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(die)
    r = side // 6
    d.rounded_rectangle((0, 0, side - 1, side - 1), radius=r, fill=(250, 250, 248, 255), outline=(200, 200, 196, 255), width=3)
    pr = side // 11
    for px, py in PIPS[n]:
        cx, cy = px * side, py * side
        d.ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=(214, 60, 60, 255) if n == 1 else (30, 30, 34, 255))
    shadow = Image.new("RGBA", (side + 60, side + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((30, 30, side + 29, side + 29), radius=r, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18)).rotate(angle, resample=Image.BICUBIC, expand=True)
    die = die.rotate(angle, resample=Image.BICUBIC, expand=True)
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.alpha_composite(shadow, ((SIZE - shadow.width) // 2 + 10, (SIZE - shadow.height) // 2 + 16))
    out.alpha_composite(die, ((SIZE - die.width) // 2, (SIZE - die.height) // 2))
    return out


def _face(n: int, angle: float = 0.0, scale: float = 1.0) -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), BG + (255,))
    canvas.alpha_composite(_die(n, angle, scale))
    return canvas


def _cover() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), BG + (255,))
    canvas.alpha_composite(_die(5, -14, 0.7), (-90, -10))
    canvas.alpha_composite(_die(2, 12, 0.7), (90, 20))
    return canvas


def build(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for n in range(1, 7):
        _face(n).convert("RGB").save(os.path.join(out_dir, f"face{n}.png"))
    _cover().convert("RGB").save(os.path.join(out_dir, "cover.png"))
    frames = []
    seq = [1, 4, 2, 6, 3, 5, 1, 3, 6, 2, 4, 5, 6, 1, 2, 3]
    for i, n in enumerate(seq):
        angle = (i * 37) % 360
        scale = 0.9 + 0.1 * math.sin(i / len(seq) * 2 * math.pi)
        frames.append(_face(n, angle, scale).convert("P", palette=Image.ADAPTIVE, colors=64))
    frames[0].save(os.path.join(out_dir, "dice.gif"), save_all=True, append_images=frames[1:],
                   duration=70, loop=0, optimize=False)


if __name__ == "__main__":
    build("assets")
