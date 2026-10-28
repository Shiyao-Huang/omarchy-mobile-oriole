<!-- SPDX-License-Identifier: MIT -->
# Pixel 6 cellular userspace

The full acceptance target remains China Mobile SIM registration, usable 4G/5G
data for Agent API traffic, and voice calls with two-way audio, including
reconnect and reboot. Neither a loaded CPIF module nor a built userspace plugin
proves this target.

## Pinned source preparation

The licensed ModemManager path uses:

- [ModemManager upstream](https://gitlab.freedesktop.org/mobile-broadband/ModemManager),
  commit `7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a`;
- [Nura's downstream patch series](https://github.com/TheNoswad/pixel6-mainline-nura/tree/a74e18dec7598f65cd504f0c75c10b8d7fc4422b/temp/modemmanager),
  commit `a74e18dec7598f65cd504f0c75c10b8d7fc4422b`.

With both checkouts at those revisions:

```sh
tools/prepare-oriole-modemmanager /path/to/nura /path/to/ModemManager
# Only in a clean disposable upstream checkout:
tools/prepare-oriole-modemmanager --apply /path/to/nura /path/to/ModemManager
```

The helper parses the pinned APKBUILD checksum list as data. It checks all
three SHA-512 hashes, applies the patches in a temporary worktree, and checks
the plugin option, SQLite carrier dependency and SIT, bearer, SIM, carrier,
IMS, SMS and voice source files. The default leaves the target unchanged.
The explicit apply operation rejects a dirty target.

On 2026-10-28, the actual upstream checkout passed preparation. Changed patch,
wrong revision and repeated apply to a dirty target were rejected without
changing the target. See the [validation contract](../experiments/gs101-modemmanager-plan.json).

## Runtime layers still to integrate

| Layer | Current evidence | Remaining acceptance |
| --- | --- | --- |
| GS101 CPIF | Matching kernel module compiled in R6 | Guarded probe, firmware handover, stable CP online state |
| CP boot daemon and remote file service | Existing Pixel 7 implementation uses stock cbd/rfsd and RAM copies of NV; GS101-specific review required | Own Pixel 6 firmware, exact GS101 ABI and power sequence; protected partitions stay read-only |
| Shannon ModemManager | Exact licensed source prepared; ARM64 build underway | Daemon/plugin builds and tests, live SIM registration and bearer traffic |
| VoLTE/voice audio | Nura describes separate AoC PCM helper, UCM routing and callaudiod | IMS registration and actual two-way call audio on China Mobile |

The reference's tinycbd package explicitly describes its pinned source as
unlicensed. This public project does not copy or bundle it. The existing stock
cbd/rfsd extraction path is a candidate for using the owner's own factory image;
it is not yet validated for this Pixel 6. Pixel 7 S5300 assumptions must not be
substituted for Pixel 6 S5123 board data.

The first actual ARM64 configure attempt stopped on missing development
packages. A separate dependency image now includes bash-completion, polkit and GObject
introspection plus libxslt/DocBook for generated headers; the ARM64 rebuild
retains strict polkit authorization.
No ModemManager or CP boot service has been installed or started on the phone
by this preparation step.

## 5G mode gap in the reference

The pinned `mm-broadband-modem-shannon.c` declares 5GNR hardware capability,
but `SHANNON_PREF_NTW_TYPE` is fixed at 9 (the source labels this LTE/GSM/WCDMA),
`SHANNON_NR_MODE` is fixed at 1 (the source labels this NSA-only), and the
reported supported/current mode masks include only 2G/3G/4G. The initial power-up
sequence sends those fixed values. This is source evidence of an incomplete
network-mode interface, not evidence of a successful China Mobile 5G session.

Before closing the 5G goal, validate the GS101 SIT network-mode payload against
a licensed reference or the owner's stock behavior, add consistent mode
selection/reporting, and observe actual NR registration and bearer traffic.
SA, NSA and LTE fallback must be distinguished; a hardware-capability bit or
an LTE bearer cannot be used to claim 5G acceptance.
