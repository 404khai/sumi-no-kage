#!/bin/zsh
# Render showcase shots with the real Godot renderer (opens a window briefly).
#   tools/capture_godot.sh [shots] [out_dir]
set -e
ROOT=${0:A:h:h}
GODOT=${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}
SHOTS=${1:-hero,env,env_wide,char_front,char_34,char_back,hands,vfx_slash,vfx_step,char_knight,char_viking,lineup,halberd,handblades}
OUT=${2:-$ROOT/docs/renders}
LOG=$ROOT/build/reports/capture.log
mkdir -p $ROOT/build/reports
"$GODOT" --path "$ROOT/game" --resolution 1600x900 -- --shots=$SHOTS --out=$OUT > $LOG 2>&1 &
PID=$!
for i in {1..120}; do sleep 1; kill -0 $PID 2>/dev/null || break; done
if kill -0 $PID 2>/dev/null; then kill $PID; echo "capture timed out"; exit 1; fi
grep -E "capture|ERROR|SCRIPT ERROR" $LOG || true
