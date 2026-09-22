from pathlib import Path

path = Path("tests/acceptance/test_shape_variants.py")

text = path.read_text(encoding="utf-8")


# ---------------------------------------------------------
# Import component_name
# ---------------------------------------------------------

old_import = "from lowkey_artifact_builder.formats.threemf import CORE_NS"

new_import = """from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    component_name,
)"""

if "component_name" not in text:
    if old_import not in text:
        raise SystemExit("Cannot find the existing threemf CORE_NS import.")

    text = text.replace(
        old_import,
        new_import,
        1,
    )


# ---------------------------------------------------------
# Migrate stale 3MF component names
# ---------------------------------------------------------

replacements = {
    '"ornament-shape-base-white"': 'component_name("ornament-shape", "base", "white")',
    '"ornament-shape-ridge-white"': 'component_name("ornament-shape", "ridge", "white")',
    '"multi-variant-shape-base-white"': 'component_name("multi-variant-shape", "base", "white")',
    '"multi-variant-shape-ridge-white"': 'component_name("multi-variant-shape", "ridge", "white")',
    '"default-shape-base-white"': 'component_name("default-shape", "base", "white")',
    '"default-shape-ridge-white"': 'component_name("default-shape", "ridge", "white")',
}


replacement_count = 0

for old, new in replacements.items():
    count = text.count(old)

    if count:
        text = text.replace(
            old,
            new,
        )
        replacement_count += count
        print(f"{count:2}  {old}")

    elif new in text:
        print(f"OK  already migrated: {new}")

    else:
        raise SystemExit(f"Cannot find old or migrated expression:\n{old}")


path.write_text(
    text,
    encoding="utf-8",
)

print()
print(f"Updated {path}")
print(f"Applied {replacement_count} naming replacements.")
