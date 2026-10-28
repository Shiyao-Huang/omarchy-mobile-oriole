# Oriole GS101 kernel preparation

The Pixel 6 needs the GS101 kernel baseline from M8 before an Omarchy image
can provide GPU acceleration, BCM4389 Wi-Fi, Shannon CPIF cellular support or
the GS101 camera path. The current Omarchy kernel head is GS201-oriented and is
rejected by [`tools/check-oriole-kernel-source`](../tools/check-oriole-kernel-source).

The 38 GPL kernel patches are maintained in the public Nura reference tree:

- source: <https://github.com/m8l8th814n-eng/gs101-mainline>
- exact source commit: `850061c79264d018317e9f849701f165e138e20c`
- patch series: <https://github.com/TheNoswad/pixel6-mainline-nura/tree/a74e18dec7598f65cd504f0c75c10b8d7fc4422b/device/testing/linux-postmarketos-gs101>

`tools/prepare-oriole-kernel` checks both pinned revisions and applies all
38 patches sequentially in a temporary worktree by default. Pass
`--apply` only in a disposable kernel worktree after the check passes. The
script never fetches firmware, reads modem partitions, changes a phone or
creates a boot image. The M8 tree's `bcmdhd`, CPIF and camera code still need
the user's own factory firmware/calibration and separate hardware gates.

The online source recheck is recorded in
[`experiments/gs101-online-source-check.json`](../experiments/gs101-online-source-check.json):
the exact M8 tree and all 38 Nura patches apply cleanly. This remains a source
checkpoint; that Mac check did not produce a Linux kernel. On 2026-10-28,
the existing Linux builder was recovered and the pinned sources were fetched
into a separate build directory. Its actual build is tracked in
[`gs101-build-repair-plan.json`](../experiments/gs101-build-repair-plan.json).

After preparation, the public Linux workflow applies the verified GS101
Panfrost cold-start MMU fix from `experiments/apply-gpu-g15.py` and runs its
failure-injection test before building. `tools/build-oriole-kernel` reads
Nura's pinned base configuration and literal `_extra_config` assignments,
then merges `kernel/configs/oriole-gs101-mainline.fragment`. It does not
execute the APKBUILD. The source must be a disposable prepared tree with no
existing `.config`; the output directory must be new.

The main build does **not** compile the external `bcmdhd`, `samsung-iommu`,
`modem`, `gps`, `trusty`, `gsa`, `aoc` or `cs35l41dna` directories. The helper
builds and installs each explicitly, including the Trusty/GSA symbol tables
needed by AoC. Their build parameters are passed on the make command line;
putting them in a main-tree configuration fragment does not enable them.
The completed output includes Image, the Oriole DTB, resolved configuration,
kernel release, matching module archive and SHA-256 checksums.

The helper defaults to cross GCC and four build jobs. The CI workflow uses
LLVM with the same helper. These are separate toolchains and their binaries
are not expected to match. Neither path creates a flashable Android boot
image or contacts a phone. Build success still needs serial recovery and
slot-B image checks before a hardware trial.
