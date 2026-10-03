import re
from pathlib import Path

FILES = [
    Path("tests/model/shape/test_artwork_fill.py"),
    Path("tests/model/shape/test_border_label.py"),
    Path("tests/model/shape/test_hole.py"),
    Path("tests/model/shape/test_inner_ridge_extrude.py"),
]


def add_raise_style_after_base_raise(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r'^(?P<indent>\s*)"shape_base_raise":'
        r"(?P<value>[^\n]+),"
        r'(?P<following>\n(?!\s*"shape_raise_style":))',
        re.MULTILINE,
    )

    matches = list(pattern.finditer(source))

    if not matches:
        print(f"SKIPPED {path}: no missing raise-style entries")
        return

    def replacement(match: re.Match[str]) -> str:
        return (
            f'{match.group("indent")}"shape_base_raise":'
            f"{match.group('value')},\n"
            f'{match.group("indent")}"shape_raise_style": "raised",'
            f"{match.group('following')}"
        )

    updated = pattern.sub(replacement, source)

    path.write_text(
        updated,
        encoding="utf-8",
    )

    print(f"UPDATED {path}: added {len(matches)} raised-style default(s)")


for file in FILES:
    add_raise_style_after_base_raise(file)


# ---------------------------------------------------------------------------
# One monkeypatched Artwork builder has a stale signature.
# ---------------------------------------------------------------------------

path = Path("tests/model/shape/test_artwork_extrusion.py")
source = path.read_text(encoding="utf-8")

test_name = "test_artwork_extrusion_passes_registered_extent_to_scad_builder"

start_marker = f"def {test_name}("
start = source.find(start_marker)

if start == -1:
    raise RuntimeError(f"{path}: could not find {test_name}")

next_test = source.find("\ndef test_", start + len(start_marker))

if next_test == -1:
    next_test = len(source)

test_source = source[start:next_test]

if "shape_raise_style: str" in test_source:
    print(f"SKIPPED {path}: target fake already accepts shape_raise_style")
else:
    old = """            shape_artwork_raise: float,
            artwork_registered_width: float,
"""

    new = """            shape_artwork_raise: float,
            shape_raise_style: str,
            artwork_registered_width: float,
"""

    count = test_source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{path}: expected exactly one stale fake signature in {test_name}; found {count}"
        )

    test_source = test_source.replace(
        old,
        new,
        1,
    )

    source = source[:start] + test_source + source[next_test:]

    path.write_text(
        source,
        encoding="utf-8",
    )

    print(f"UPDATED {path}: target Artwork builder fake")


print()
print("Done.")
