from pathlib import Path
import re
import sys


BACKGROUND_ID = "white-background"


def apply_white_fill(svg_path: Path) -> None:
    content = svg_path.read_text(encoding="utf-8")
    if BACKGROUND_ID in content:
        print(f"Skipped, already has white background: {svg_path}")
        return

    match = re.search(r"<svg\b[^>]*>", content)
    if not match:
        print(f"Error: no <svg> tag found in {svg_path}")
        sys.exit(1)

    background = (
                  f'\n  <rect id="{BACKGROUND_ID}" '
                  f'width="100%" height="100%" fill="white"/>'
                 )

    updated = content[:match.end()] + background + content[match.end():]
    svg_path.write_text(updated, encoding="utf-8")
    print(f"Updated: {svg_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python apply_white_fill.py input_file.svg")
        sys.exit(1)

    svg_path = Path(sys.argv[1])
    if not svg_path.exists():
        print(f"Error: file not found: {svg_path}")
        sys.exit(1)

    apply_white_fill(svg_path)


if __name__ == "__main__":
    main()