#!/usr/bin/env bash
set -euo pipefail

source /opt/stat-ci/revisions.env
export JOBS="${JOBS:-4}"
step="${1:?usage: install-deps.sh STEP}"
mkdir -p /opt/stat-sources "$STAT_DEPS" /opt/stat-build

clone() {
  local url="$1" sha="$2" dir="$3"
  git clone --no-checkout "$url" "/opt/stat-sources/$dir"
  git -C "/opt/stat-sources/$dir" checkout --detach "$sha"
  test "$(git -C "/opt/stat-sources/$dir" rev-parse HEAD)" = "$sha"
}

run_pixi() {
  local step="$1"
  shift
  echo "==> $step"
  pixi run --manifest-path "$STAT_PIXI/pixi.toml" bash -euo pipefail -c \
    'source /opt/stat-ci/stat-env.sh; eval "$1"' bash "$*"
}

if [ "$step" = sources ]; then
clone https://github.com/llnl/STAT.git "$STAT_SHA" STAT
clone https://github.com/LLNL/LaunchMON.git "$LAUNCHMON_SHA" LaunchMON
clone https://github.com/dyninst/mrnet.git "$MRNET_SHA" mrnet
clone https://github.com/LLNL/graphlib.git "$GRAPHLIB_SHA" graphlib
clone https://github.com/pramodk/pystack.git "$PYSTACK_SHA" pystack
clone https://github.com/dyninst/dyninst.git "$DYNINST_SHA" dyninst

binutils_version=2.41
binutils_sha=ae9a5789e23459e59606e6714723f2d3ffc31c03174191ef0d015bdf06007450
if [ ! -s "/opt/stat-downloads/binutils-$binutils_version.tar.xz" ]; then
  curl -fL --retry 3 "https://ftp.gnu.org/gnu/binutils/binutils-$binutils_version.tar.xz" \
    -o "/opt/stat-downloads/binutils-$binutils_version.tar.xz"
fi
echo "$binutils_sha  /opt/stat-downloads/binutils-$binutils_version.tar.xz" | sha256sum -c -
mkdir -p /opt/stat-sources/binutils
tar -C /opt/stat-sources/binutils --strip-components=1 \
  -xf "/opt/stat-downloads/binutils-$binutils_version.tar.xz" \
  "binutils-$binutils_version/config" \
  "binutils-$binutils_version/config.guess" \
  "binutils-$binutils_version/config.sub" \
  "binutils-$binutils_version/include" \
  "binutils-$binutils_version/install-sh" \
  "binutils-$binutils_version/libiberty" \
  "binutils-$binutils_version/missing" \
  "binutils-$binutils_version/mkinstalldirs" \
  "binutils-$binutils_version/move-if-change"
fi

if [ "$step" = libiberty ]; then
run_pixi libiberty '
  mkdir -p /opt/stat-build/libiberty
  cd /opt/stat-build/libiberty
  export CFLAGS="-g -O2 -fPIC"
  /opt/stat-sources/binutils/libiberty/configure --prefix="$STAT_DEPS" --enable-install-libiberty
  make -j "$JOBS"
  make install
'
fi

if [ "$step" = python-tools ]; then
run_pixi python-tools '
  python -m pip install --no-deps --only-binary=:all: "py-spy==0.4.0"
  python -m pip install --no-deps "xdot==1.0"
  glib-compile-schemas "$PIXI_PREFIX/share/glib-2.0/schemas"
  dot -c
'
fi

if [ "$step" = pystack ]; then
run_pixi pystack '
  # The fork enables LTO, but conda-forge binutils cannot load GCC LTO objects
  # into nanobind-static on this toolchain. Keep the pinned source unchanged on
  # disk outside this image; patch only its disposable container checkout.
  sed -i "/set(CMAKE_CXX_FLAGS_RELEASE.*-flto/d; /set(CMAKE_CXX_FLAGS_RELWITHDEBINFO.*-flto/d" \
    /opt/stat-sources/pystack/CMakeLists.txt
  python -m pip install --prefix="$STAT_DEPS" --no-build-isolation --no-deps /opt/stat-sources/pystack
'
fi

if [ "$step" = dyninst ]; then
run_pixi dyninst '
  libiberty_lib="$(find "$STAT_DEPS" \( -name libiberty.a -o -name libiberty.so \) -print -quit)"
  test -n "$libiberty_lib"
  cmake -S /opt/stat-sources/dyninst -B /opt/stat-build/dyninst \
    -DCMAKE_INSTALL_PREFIX="$STAT_DEPS" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_PREFIX_PATH="$STAT_DEPS;$PIXI_PREFIX" \
    -DBoost_ROOT_DIR="$PIXI_PREFIX" \
    -DElfUtils_ROOT_DIR="$PIXI_PREFIX" \
    -DLibIberty_ROOT_DIR="$STAT_DEPS" \
    -DLibIberty_LIBRARIES="$libiberty_lib" \
    -DTBB_ROOT_DIR="$PIXI_PREFIX" \
    -DUSE_OpenMP=ON \
    -DENABLE_STATIC_LIBS=OFF \
    -DCMAKE_INSTALL_RPATH="$STAT_DEPS/lib;$PIXI_PREFIX/lib"
  cmake --build /opt/stat-build/dyninst -j "$JOBS"
  cmake --install /opt/stat-build/dyninst
'
fi

if [ "$step" = graphlib ]; then
run_pixi graphlib '
  cmake -S /opt/stat-sources/graphlib -B /opt/stat-build/graphlib \
    -DCMAKE_INSTALL_PREFIX="$STAT_DEPS" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DCMAKE_INSTALL_RPATH="$STAT_DEPS/lib;$PIXI_PREFIX/lib"
  cmake --build /opt/stat-build/graphlib -j "$JOBS"
  cmake --install /opt/stat-build/graphlib
'
fi

if [ "$step" = mrnet ]; then
run_pixi mrnet '
  cd /opt/stat-sources/mrnet
  if test -x ./bootstrap; then ./bootstrap;
  elif ! test -x ./configure; then autoreconf -ivf; fi
  mkdir -p /opt/stat-build/mrnet
  cd /opt/stat-build/mrnet
  export CPPFLAGS="-I$PIXI_PREFIX/include"
  export CXXFLAGS="-I$PIXI_PREFIX/include"
  export SOFLAGS="-L$PIXI_PREFIX/lib -Wl,-rpath,$PIXI_PREFIX/lib"
  export LDFLAGS="$SOFLAGS"
  /opt/stat-sources/mrnet/configure --prefix="$STAT_DEPS" --enable-shared
  make -j1
  make install
'
fi

if [ "$step" = launchmon ]; then
run_pixi launchmon '
  cd /opt/stat-sources/LaunchMON
  ./bootstrap
  mkdir -p /opt/stat-build/launchmon
  cd /opt/stat-build/launchmon
  export ACLOCAL_PATH="$PIXI_PREFIX/share/aclocal:${ACLOCAL_PATH:-}"
  export CPPFLAGS="-I$PIXI_PREFIX/include"
  export CFLAGS="$CPPFLAGS"
  export CXXFLAGS="-std=gnu++14 $CPPFLAGS"
  export LDFLAGS="-L$PIXI_PREFIX/lib -Wl,-rpath,$PIXI_PREFIX/lib"
  /opt/stat-sources/LaunchMON/configure --prefix="$STAT_DEPS" --with-test-rm=slurm
  make -j "$JOBS"
  make install
'

test -f "$STAT_DEPS/include/walker.h"
test -f "$STAT_DEPS/include/graphlib.h"
test -x "$STAT_DEPS/bin/mrnet_commnode"
test -x "$STAT_DEPS/bin/launchmon"
fi
