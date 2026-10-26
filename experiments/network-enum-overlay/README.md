# Offline PCIe1 enumeration candidate

This is **not installed** and is not a Wi-Fi connectivity result. See
[plan](../network-supply-owner-plan.json) and
[evidence](../network-supply-owner-evidence.json). A fresh off-device backup now exists. The first hardware attempt failed address
translation and cleaned up; this revision adds the missing HSI2 parent mapping.
The corrected hardware retry parsed the range successfully but failed at PMU
bit10 readback. Endpoint enumeration and Wi-Fi remain unproven.

Use the exact kernel source/config/Module.symvers of the target. Build in a new
external directory containing these source files (including `parent-range.inc`), with `KERNEL_SRC` and
`KERNEL_OUT` set to the verified source/output paths and `ENUM_BUILD` set to that
new directory. The source tested against Linux 7.3.0-rc6-omamobile-oriole-m1.

```sh
aarch64-linux-gnu-gcc -E -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
  -I"$KERNEL_SRC/include" "$ENUM_BUILD/wifi.dts" > "$ENUM_BUILD/wifi.pre.dts"
dtc -@ -I dts -O dtb -o "$ENUM_BUILD/wifi.dtbo" "$ENUM_BUILD/wifi.pre.dts"
fdtoverlay -i "$KERNEL_OUT/arch/arm64/boot/dts/exynos/google/gs101-oriole.dtb" \
  -o "$ENUM_BUILD/wifi-merged.dtb" "$ENUM_BUILD/wifi.dtbo"
python3 - "$ENUM_BUILD" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
b = (p / 'wifi.dtbo').read_bytes()
(p / 'wifi_dtbo.h').write_text(
    '/* Generated from wifi.dts. */\n'
    'static const unsigned char wifi_dtbo[] __aligned(8) = {\n'
    + ','.join('0x%02x' % v for v in b) + '\n};\n')
PY
make -C "$KERNEL_SRC" O="$KERNEL_OUT" ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- M="$ENUM_BUILD" W=1 -j2 modules
```

Successful compilation proves neither wiring nor safe DMA. The merged tree must
resolve the Oriole board, domain 1, IRQ 509, stock register ranges, GPIO polarities
and supply/PHY phandles. No modem0, IOMMU, S2MPU or DMA-pool changes are included.
There is deliberately no `module_exit`: the DT remains until reboot. Host/PHY
cleanup is independently required to release the WLAN rail. Endpoint driver
loading must be blocked during any future enumeration-only test.
