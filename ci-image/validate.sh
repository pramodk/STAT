#!/usr/bin/env bash
set -euo pipefail
source /opt/stat-ci/stat-env.sh
prefix="${1:-/opt/stat-baseline}"
test -x "$prefix/bin/stat-cl"
test -x "$STAT_DEPS/bin/launchmon"
test -x "$STAT_DEPS/bin/mrnet_commnode"
test -f "$STAT_DEPS/lib/liblnlgraph.so"
pixi run --manifest-path "$STAT_PIXI/pixi.toml" bash -euo pipefail -c '
  source /opt/stat-ci/stat-env.sh
  export PATH="$1/bin:$PATH"
  export PYTHONPATH="$1/lib/python3.11/site-packages:$PYTHONPATH"
  python -c "import STAT, cairo, gi, xdot; gi.require_version(\"Gtk\", \"3.0\"); from gi.repository import Gtk"
  stat-cl --help >/dev/null 2>&1
  stat_so="$(find "$1" -name "_STAT*.so" -print -quit)"
  test -n "$stat_so"
  ! ldd "$stat_so" | grep -q "not found"
  py-spy --version >/dev/null
  python -c "import pystack"
' bash "$prefix"
