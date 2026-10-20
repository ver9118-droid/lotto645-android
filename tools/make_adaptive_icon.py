"""레거시 아이콘(assets/icon.png)에서 Android 적응형 아이콘을 만듭니다.

실행:  python tools/make_adaptive_icon.py

- assets/icon_fg.png : 투명 배경 + 중앙 안전 영역(66%) 안에 들어간 꽃/6-45
- assets/icon_bg.png : 흰색 단색 배경

adaptive 아이콘은 Android 8.0(API 26)+ 런처에서 사용되며,
그 이전 버전은 icon.filename(assets/icon.png)을 그대로 씁니다.

레거시 아이콘은 바깥이 투명하고, 안쪽에 회색 테두리를 가진 흰 둥근 사각형이
그려져 있습니다. 테두리와 흰 배경을 바깥에서부터 flood fill 로 지워
꽃과 글자만 남깁니다.
"""
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SIZE = 512      # 리소스 크기(런처가 알아서 축소)
SAFE = 336      # 안전 영역: 108dp 중 72dp(66%)에 해당


def is_background(pixel: tuple[int, int, int, int]) -> bool:
    """바깥에서 안쪽으로 퍼져나가며 지워도 되는 픽셀인지 판단합니다."""
    r, g, b, a = pixel
    return a < 200 or min(r, g, b) >= 220


def clear_background(img: Image.Image) -> Image.Image:
    """가장자리에서 시작해 배경/테두리를 투명하게 만듭니다.

    꽃 안쪽의 흰 원은 꽃잎에 둘러싸여 바깥과 연결되지 않으므로 그대로 남습니다.
    """
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    queue: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        idx = y * w + x
        if not seen[idx] and is_background(px[x, y]):
            seen[idx] = 1
            queue.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while queue:
        x, y = queue.popleft()
        px[x, y] = (0, 0, 0, 0)
        if x > 0:
            push(x - 1, y)
        if x + 1 < w:
            push(x + 1, y)
        if y > 0:
            push(x, y - 1)
        if y + 1 < h:
            push(x, y + 1)

    return img


def make_foreground(src: Image.Image) -> Image.Image:
    img = clear_background(src.convert("RGBA"))

    bbox = img.getbbox()
    if bbox is None:
        raise SystemExit("아이콘에서 내용을 찾지 못했습니다.")
    content = img.crop(bbox)

    scale = min(SAFE / content.width, SAFE / content.height)
    content = content.resize(
        (max(1, round(content.width * scale)), max(1, round(content.height * scale))),
        Image.LANCZOS,
    )

    fg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    fg.alpha_composite(
        content,
        ((SIZE - content.width) // 2, (SIZE - content.height) // 2),
    )
    return fg


def main() -> None:
    src = Image.open(ASSETS / "icon.png")
    make_foreground(src).save(ASSETS / "icon_fg.png", optimize=True)

    bg = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    bg.save(ASSETS / "icon_bg.png", optimize=True)

    for name in ("icon_fg.png", "icon_bg.png"):
        path = ASSETS / name
        print(f"{name}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
