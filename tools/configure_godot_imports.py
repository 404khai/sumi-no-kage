#!/usr/bin/env python3
"""Pin Godot import settings for every exported asset (CLI-first: no editor dock).

Run after the first `godot --import` has created the .import files:
    python3 tools/configure_godot_imports.py && godot --headless --path game --import
Idempotent; only rewrites keys it owns.
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COMMON = {
    "import_script/path": '"res://tools/import/ink_post_import.gd"',
    "meshes/ensure_tangents": "false",      # no normal maps in the ink look
    "meshes/generate_lods": "true",
    "meshes/create_shadow_meshes": "true",
}
PER_KIND = {
    "character": {"animation/import_rest_as_RESET": "true", "meshes/light_baking": "0"},
    "weapon": {"meshes/light_baking": "0"},
    "environment": {"meshes/light_baking": "1"},
}


def main():
    manifest = json.load(open(os.path.join(ROOT, "tools", "asset_manifest.json")))
    for asset in manifest["assets"]:
        path = os.path.join(ROOT, asset["output"] + ".import")
        if not os.path.exists(path):
            print(f"[imports] skip {asset['id']}: run `godot --headless --path game --import` first")
            continue
        text = open(path).read()
        wanted = dict(COMMON, **PER_KIND.get(asset["kind"], {}))
        for key, value in wanted.items():
            pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
            line = f"{key}={value}"
            text = pat.sub(line, text) if pat.search(text) else text.replace("[params]\n", f"[params]\n\n{line}\n", 1)
        open(path, "w").write(text)
        print(f"[imports] configured {asset['id']}")


if __name__ == "__main__":
    main()
