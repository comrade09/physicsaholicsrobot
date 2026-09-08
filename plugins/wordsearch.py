"""
games/wordsearch.py
---------------------
Generates a word-search puzzle image locally with Pillow.

NOTE ON "use any api to get that image": there isn't a reliable free public
API for generating word-search puzzle images, so instead of depending on a
third-party service that can go down or rate-limit you, this renders the
grid directly with Pillow. It's faster, free, and always works offline.
If you'd rather call an external image API, swap `render_grid_image()` for
an aiohttp call and feed the returned bytes into `message.reply_photo`.
"""
import random
import string
import io
from PIL import Image, ImageDraw, ImageFont

WORD_POOL = [
    "PYTHON", "TELEGRAM", "AURA", "KARMA", "GAME", "WINNER", "BOT", "CODE",
    "MONGO", "POINT", "GROUP", "QUEST", "LEVEL", "BONUS", "SCORE", "PUZZLE",
]


def generate_grid(size: int = 10, word_count: int = 5):
    words = random.sample(WORD_POOL, word_count)
    grid = [['' for _ in range(size)] for _ in range(size)]
    directions = [(0, 1), (1, 0), (1, 1), (-1, 1)]
    placed = []

    for word in words:
        for _ in range(60):
            dr, dc = random.choice(directions)
            r = random.randint(0, size - 1)
            c = random.randint(0, size - 1)
            er, ec = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
            if not (0 <= er < size and 0 <= ec < size):
                continue
            ok = True
            for i in range(len(word)):
                rr, cc = r + dr * i, c + dc * i
                if grid[rr][cc] not in ('', word[i]):
                    ok = False
                    break
            if ok:
                for i in range(len(word)):
                    rr, cc = r + dr * i, c + dc * i
                    grid[rr][cc] = word[i]
                placed.append(word)
                break

    for r in range(size):
        for c in range(size):
            if grid[r][c] == '':
                grid[r][c] = random.choice(string.ascii_uppercase)

    return grid, placed


def render_grid_image(grid) -> io.BytesIO:
    size = len(grid)
    cell = 48
    img_size = size * cell
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            font = ImageFont.truetype(path, 26)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    for r in range(size):
        for c in range(size):
            x0, y0 = c * cell, r * cell
            draw.rectangle([x0, y0, x0 + cell, y0 + cell], outline="#cccccc")
            letter = grid[r][c]
            bbox = draw.textbbox((0, 0), letter, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                (x0 + (cell - w) / 2, y0 + (cell - h) / 2 - bbox[1]),
                letter, fill="black", font=font
            )

    buf = io.BytesIO()
    buf.name = "wordsearch.png"
    img.save(buf, "PNG")
    buf.seek(0)
    return buf
