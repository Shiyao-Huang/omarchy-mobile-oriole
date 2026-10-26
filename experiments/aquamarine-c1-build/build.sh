#!/bin/bash
set -euo pipefail
ulimit -s 65536
export QEMU_STACK_SIZE=67108864
rm -f /var/lib/pacman/db.lck
pacman -S --noconfirm --needed cmake ninja hyprwayland-scanner hyprutils seatd libinput wayland wayland-protocols pixman libdrm mesa libdisplay-info hwdata > /out/dependencies.log 2>&1
pacman -Qk llvm-libs > /out/llvm-check.log 2>&1
pacman -Q > /out/build-clean-packages.txt
cmake -S /src -B /out/build-clean -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr > /out/configure.log 2>&1
cmake --build /out/build-clean --target aquamarine attachments output commitThread -j2 > /out/build-clean.log 2>&1
ctest --test-dir /out/build-clean --output-on-failure -R '^(attachments|output|commitThread)$' > /out/tests.log 2>&1
file /out/build-clean/libaquamarine.so.0.15.1 > /out/artifact.txt
sha256sum /out/build-clean/libaquamarine.so.0.15.1 >> /out/artifact.txt
readelf -d /out/build-clean/libaquamarine.so.0.15.1 >> /out/artifact.txt
