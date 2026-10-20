"""앱에서 실제로 쓰는 글자만 남겨 한글 폰트를 서브셋합니다.

실행:  python tools/subset_fonts.py

- 입력: font_src/NanumGothic-{Regular,Bold}.ttf (전체 폰트, APK 에는 미포함)
- 출력: assets/NanumGothic-{Regular,Bold}.ttf (서브셋, APK 에 포함)

문구를 추가/수정한 뒤에는 이 스크립트를 다시 실행해 주세요.
서브셋에 없는 글자는 화면에서 네모(□)로 보입니다.
"""
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "font_src"
OUT = ROOT / "assets"
TMP_CHARS = ROOT / ".font-chars.txt"

# UI 코드에 등장하는 모든 문자 + ASCII + 자주 쓰는 기호
EXTRA = "·—–…→≈▼×％"


def collect_chars() -> str:
    chars = {chr(i) for i in range(32, 127)}
    chars.update(EXTRA)

    sources = [ROOT / "main.py"]
    sources += sorted((ROOT / "src").rglob("*.py"))
    for path in sources:
        chars.update(path.read_text(encoding="utf-8"))

    chars.discard("\x00")
    return "".join(sorted(chars))


def subset_font(src: Path, dst: Path, chars_file: Path) -> None:
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.notdef_glyph = True
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.drop_tables = []  # OS/2, post 등 유지

    font = subset.load_font(str(src), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=chars_file.read_text(encoding="utf-8"))
    subsetter.subset(font)
    subset.save_font(font, str(dst), options)


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit(
            "font_src/ 폴더에 전체 폰트가 필요합니다.\n"
            "NanumGothic-Regular.ttf / NanumGothic-Bold.ttf 를 넣어 주세요."
        )

    chars = collect_chars()
    TMP_CHARS.write_text(chars, encoding="utf-8")
    print(f"사용 글자 수: {len(chars):,}")

    try:
        for name in ("NanumGothic-Regular.ttf", "NanumGothic-Bold.ttf"):
            src, dst = SRC / name, OUT / name
            subset_font(src, dst, TMP_CHARS)
            before, after = src.stat().st_size, dst.stat().st_size
            print(f"{name}: {before:,} -> {after:,} bytes")
    finally:
        TMP_CHARS.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
