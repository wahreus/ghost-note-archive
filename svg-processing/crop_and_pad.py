from pathlib import Path
import io
import re
import sys

import cairosvg
from PIL import Image


PADDING = 10
WHITE_THRESHOLD = 245
MAX_GAP_BETWEEN_CONTENT_ROWS = 10
MIN_CONTENT_BAND_HEIGHT = 3
BACKGROUND_ID = "white-background"


def get_attr(svg: str, attr: str) -> str | None:
    match = re.search(rf'\b{attr}="([^"]+)"', svg)
    return match.group(1) if match else None


def get_number(value: str) -> float:
    match = re.match(r"\s*([\d.]+)", value)
    if not match:
        raise ValueError(f"Could not read number from: {value}")
    return float(match.group(1))


def get_viewbox(svg: str, width: float, height: float) -> tuple[float, float, float, float]:
    viewbox = get_attr(svg, "viewBox")
    if not viewbox:
        return 0.0, 0.0, width, height
    values = [float(value) for value in viewbox.split()]
    if len(values) != 4:
        raise ValueError("Invalid viewBox.")
    return values[0], values[1], values[2], values[3]


def set_attr(svg: str, attr: str, value: str) -> str:
    if re.search(rf'\b{attr}="[^"]+"', svg):
        return re.sub(rf'\b{attr}="[^"]+"', f'{attr}="{value}"', svg, count=1)
    return re.sub(r"(<svg\b[^>]*?)>", rf'\1 {attr}="{value}">', svg, count=1)


def row_has_content(image: Image.Image, y: int) -> bool:
    pixels = image.load()
    width, _ = image.size
    for x in range(width):
        r, g, b = pixels[x, y]
        if r < WHITE_THRESHOLD or g < WHITE_THRESHOLD or b < WHITE_THRESHOLD:
            return True
    return False


def find_content_rows(image: Image.Image) -> tuple[int, int] | None:
    rows = [y for y in range(image.height) if row_has_content(image, y)]
    if not rows:
        return None
    bands = []
    start = rows[0]
    previous = rows[0]
    for y in rows[1:]:
        if y - previous <= MAX_GAP_BETWEEN_CONTENT_ROWS:
            previous = y
        else:
            bands.append((start, previous))
            start = y
            previous = y
    bands.append((start, previous))
    real_bands = [
        (start, end)
        for start, end in bands
        if end - start + 1 >= MIN_CONTENT_BAND_HEIGHT
    ]
    if not real_bands:
        real_bands = bands
    top = min(start for start, _ in real_bands)
    bottom = max(end for _, end in real_bands)
    top = max(0, top - PADDING)
    bottom = min(image.height - 1, bottom + PADDING)
    return top, bottom


def update_white_background(svg: str,
                            x: float,
                            y: float,
                            width: float,
                            height: float,
                            ) -> str:
    rect = (
            f'<rect id="{BACKGROUND_ID}" '
            f'x="{x:.2f}" y="{y:.2f}" '
            f'width="{width:.2f}" height="{height:.2f}" '
            f'fill="white"/>'
            )

    pattern = rf'<rect\b[^>]*id="{BACKGROUND_ID}"[^>]*/?>'
    if re.search(pattern, svg):
        return re.sub(pattern, rect, svg, count=1)
    return re.sub(r"(<svg\b[^>]*>)", r"\1\n  " + rect, svg, count=1)


def crop_svg_vertical(svg_path: Path) -> None:
    svg = svg_path.read_text(encoding="utf-8")
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    rgba = Image.open(io.BytesIO(png)).convert("RGBA")
    white_background = Image.new("RGBA", rgba.size, "white")
    image = Image.alpha_composite(white_background, rgba).convert("RGB")

    content_rows = find_content_rows(image)
    if content_rows is None:
        print(f"Skipped, no non-white content found: {svg_path}")
        return

    top, bottom = content_rows
    width_attr = get_attr(svg, "width")
    height_attr = get_attr(svg, "height")
    if not width_attr or not height_attr:
        raise ValueError("SVG must have width and height attributes.")

    old_width = get_number(width_attr)
    old_height = get_number(height_attr)
    viewbox_x, viewbox_y, viewbox_width, viewbox_height = get_viewbox(svg,
                                                                      old_width,
                                                                      old_height,
                                                                      )

    horizontal_padding = (PADDING / image.width) * viewbox_width

    new_viewbox_x = viewbox_x - horizontal_padding
    new_viewbox_width = viewbox_width + (horizontal_padding * 2)
    new_viewbox_y = viewbox_y + (top / image.height) * viewbox_height
    new_viewbox_height = ((bottom - top + 1) / image.height) * viewbox_height
    new_width = old_width * (new_viewbox_width / viewbox_width)
    new_height = old_height * (new_viewbox_height / viewbox_height)

    svg = set_attr(svg,
                   "viewBox",
                   (f"{new_viewbox_x:.2f} "
                    f"{new_viewbox_y:.2f} "
                    f"{new_viewbox_width:.2f} "
                    f"{new_viewbox_height:.2f}"
                    )
                   )

    svg = set_attr(svg, "width", f"{new_width:.2f}")
    svg = set_attr(svg, "height", f"{new_height:.2f}")
    svg = update_white_background(
                                  svg,
                                  new_viewbox_x,
                                  new_viewbox_y,
                                  new_viewbox_width,
                                  new_viewbox_height,
                                  )

    svg_path.write_text(svg, encoding="utf-8")
    print(f"Cropped: {svg_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python crop_svg_vertical.py input_file.svg")
        sys.exit(1)
    svg_path = Path(sys.argv[1])
    if not svg_path.exists():
        print(f"Error: file not found: {svg_path}")
        sys.exit(1)
    crop_svg_vertical(svg_path)


if __name__ == "__main__":
    main()