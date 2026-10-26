#!/bin/bash
set -euo pipefail
ulimit -s 65536
export QEMU_STACK_SIZE=67108864
pacman -Syu --noconfirm --needed meson python-mako python-ply python-packaging python-yaml python-pycparser gtest llvm clang libclc spirv-llvm-translator spirv-tools glslang libxrandr xcb-util-keysyms > /out/dependencies.log 2>&1
pacman -Q > /out/packages.txt
meson setup /out/build /src --prefix=/opt/oriole-experiments/mesa-g10 --libdir=lib --buildtype=release --optimization=2 -Db_ndebug=true -Dgallium-drivers=panfrost,llvmpipe,softpipe -Dllvm=enabled -Dvulkan-drivers= -Dplatforms=x11,wayland -Dglx=dri -Degl=enabled -Dgbm=enabled -Dgles1=disabled -Dgles2=enabled -Dgallium-va=disabled -Dgallium-rusticl=false -Dlibunwind=disabled -Dvalgrind=disabled -Dhtml-docs=disabled -Dbuild-tests=true > /out/configure.log 2>&1
ninja -C /out/build -j4 src/egl/libEGL_mesa.so.0.0.0 src/gallium/targets/dri/libgallium-26.2.4-oriole.g10.so src/gallium/targets/dril/libdril_dri.so src/gbm/backends/dri/dri_gbm.so src/gbm/libgbm.so.1.0.0 src/glx/libGLX_mesa.so.0.0.0 src/panfrost/compiler/bifrost/test/bifrost_tests src/panfrost/compiler/bifrost/valhall/test/valhall_tests src/panfrost/compiler/bifrost/valhall/valhall_disasm_test src/panfrost/genxml/cs_builder_tests src/panfrost/lib/panfrost_attribute_test src/panfrost/lib/panfrost_blend_test src/panfrost/lib/panfrost_clear_test src/panfrost/lib/panfrost_tests src/panfrost/shared/panfrost_tiling > /out/build.log 2>&1
meson test -C /out/build --list > /out/test-list.txt
DESTDIR=/out/stage meson install -C /out/build --no-rebuild > /out/install.log 2>&1
find /out/stage -type f -exec sha256sum {} \; > /out/artifact-hashes.txt
echo BUILD_COMPLETE
