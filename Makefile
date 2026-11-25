# Sumi no Kage — CLI asset pipeline. No editor needs to be open.
#   make all        textures -> sources -> glTF -> Godot import -> validation
#   make renders    turnarounds (Blender) + in-engine shots (Godot, opens a window briefly)
#   make help

BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
GODOT   ?= /Applications/Godot.app/Contents/MacOS/Godot
BL      := $(BLENDER) -b --factory-startup --python
GD      := $(GODOT) --headless --path game

.PHONY: all help textures assets kage knight viking daggers halberd handblade blades shrine export godot-import validate \
        validate-blender validate-godot renders renders-blender renders-godot clean-generated

all: textures assets export godot-import validate  ## full pipeline

help:
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

textures:  ## procedural ink textures -> game/textures/ink
	$(BL) tools/textures/generate_ink_textures.py

assets: kage knight viking daggers halberd handblade blades shrine  ## rebuild every .blend source

kage:  ## assassin: body, garments, rig, weights, rig-test actions
	$(BL) tools/blender/build_kage.py

knight:  ## Ashen Knight (shares Kage's skeleton)
	$(BL) tools/blender/build_knight.py

viking:  ## Viking berserker (shares Kage's skeleton)
	$(BL) tools/blender/build_viking.py

halberd:  ## Kurogane halberd (two-handed polearm)
	$(BL) tools/blender/build_halberd.py

blades:  ## greatsword, broadsword, naginata
	$(BL) tools/blender/build_blades.py

handblade:  ## Kuzuri katar-style handblade (pair)
	$(BL) tools/blender/build_handblade.py

daggers:  ## Kagenui dual daggers + saya
	$(BL) tools/blender/build_daggers.py

shrine:  ## Kurogane Shrine blockout
	$(BL) tools/blender/build_shrine_blockout.py

export:  ## .blend -> game/assets/**/*.glb (per tools/asset_manifest.json)
	$(BL) tools/blender/export_assets.py

godot-import:  ## import textures, build ink materials, pin import settings, import glTF
	$(GD) --import
	$(GD) --script res://tools/build_materials.gd
	python3 tools/configure_godot_imports.py
	rm -f game/.godot/imported/*.glb-*  # force glTF re-import against the freshly built materials
	$(GD) --import

validate: validate-blender validate-godot  ## both validators; reports in build/reports

validate-blender:
	$(BL) tools/validate/validate_blender.py

validate-godot:
	$(GD) --script res://tools/validate_assets.gd

renders: renders-blender renders-godot  ## refresh docs/renders

renders-blender:
	$(BL) tools/textures/render_palette.py
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_kage.py -- --preview --preview-pose
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_knight.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_viking.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_halberd.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_handblade.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_blades.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_daggers.py -- --preview
	SUMI_PREVIEW_DIR=$(CURDIR)/docs/renders/blender $(BL) tools/blender/build_shrine_blockout.py -- --preview

renders-godot:
	GODOT=$(GODOT) tools/capture_godot.sh

clean-generated:  ## delete everything the pipeline regenerates (sources are rebuilt too)
	rm -rf game/.godot build game/materials/M_*.tres game/textures/ink/*.png
	find game/assets -name '*.glb' -o -name '*.import' | xargs rm -f
	find game/textures -name '*.import' -delete
