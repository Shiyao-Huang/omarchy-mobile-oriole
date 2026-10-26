# Oriole GS101 kernel preparation

The Pixel 6 needs the GS101 kernel baseline from M8 before an Omarchy image
can provide GPU acceleration, BCM4389 Wi-Fi, Shannon CPIF cellular support or
the GS101 camera path. The current Omarchy kernel head is GS201-oriented and is
rejected by [`tools/check-oriole-kernel-source`](../tools/check-oriole-kernel-source).

The 38 GPL kernel patches are maintained in the public Nura reference tree:

- source: <https://github.com/m8l8th814n-eng/gs101-mainline>
- exact source commit: `850061c79264d018317e9f849701f165e138e20c`
- patch series: <https://github.com/TheNoswad/pixel6-mainline-nura/tree/a74e18dec7598f65cd504f0c75c10b8d7fc4422b/device/testing/linux-postmarketos-gs101>

`tools/prepare-oriole-kernel` checks both pinned revisions and runs
`git apply --check` for all 38 patches. It is read-only by default. Pass
`--apply` only in a disposable kernel worktree after the check passes. The
script never fetches firmware, reads modem partitions, changes a phone or
creates a boot image. The M8 tree's `bcmdhd`, CPIF and camera code still need
the user's own factory firmware/calibration and separate hardware gates.

The online source recheck is recorded in
[`experiments/gs101-online-source-check.json`](../experiments/gs101-online-source-check.json):
the exact M8 tree and all 38 Nura patches apply cleanly. This remains a source
checkpoint; the Mac cannot produce the required Linux kernel build because it
has no GNU Make 4+ or case-sensitive build filesystem.

After preparation, the public Linux workflow applies the verified GS101
Panfrost cold-start MMU fix from `experiments/apply-gpu-g15.py` and runs its
failure-injection test before building. Merge
`kernel/configs/oriole-gs101-mainline.fragment`, run the project's Linux build
in a Linux environment with GNU Make 4+, and keep the output separate from
other kernel worktrees. Do not flash until the build, serial recovery and
slot-B safeguards have been reviewed.
