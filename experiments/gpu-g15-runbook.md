# G15: cold first-job MMU interrupt trial

This is an experimental driver, not a complete installation package.
The validation contract is `gpu-g15-mmu-init-plan.json`; current results are
in `gpu-g15-mmu-init-evidence.json`.

Upstream Linux fix:
https://github.com/torvalds/linux/commit/8a597d099b8b2f25df655cbe8e30765013784fed

## Offline reproduction

The GPL-2.0 base MMU file is included as `gpu-g15-base-panfrost_mmu.c`.
Start with this captured G7 source whose MMU file SHA-256 is
`57f03c626bdef56726bbe14ea6fd36e1229761688ddfd8da6ec3b5ec2851e1b2`.
The G7 power-status instrumentation remains unchanged.

```sh
python3 experiments/test-gpu-g15-mmu.py experiments/gpu-g15-base-panfrost_mmu.c
python3 experiments/apply-gpu-g15.py "$G7_DIR/panfrost_mmu.c" "$NEW_MMU_FILE"
```

Copy the G7 external-module source into a new G15 directory; replace only
`panfrost_mmu.c` with the generated file. Build against the configured
`7.3.0-rc6-omamobile-oriole-m1` kernel with `ARCH=arm64`,
`CROSS_COMPILE=aarch64-linux-gnu-`, `M=<G15 directory>`, `W=1`, `-j2`.
Do not edit the original G7 directory or the shared kernel tree. Preserve
all pre-existing G7 power and platform changes. No device tree changes
are made. Run checkpatch on the diff with `--strict --no-tree --no-signoff`;
no human DCO signoff is claimed by these artifacts.

## Gated hardware sequence

1. **Read-only / low risk:** recover access and identify the phone mode.
   Check both the default ADB server and the pre-existing task-specific
   server. An empty default list does not prove no ADB connection. Read
   product and slot flags through Fastboot. Record the observation.
2. **Boot selection / recovery risk:** if B is the known Linux slot and
   its retries are exhausted, selecting the existing B slot resets retry
   allowance without flashing images. Announce before reboot. Expect the
   Linux diagnostic gate and serial port. Stop if either is absent. Keep
   Fastboot recovery available; do not format userdata.
3. **Read-only backup / low risk:** after any stock fallback, read fresh
   devinfo/efs/efs_backup/modem_userdata/persist. Verify source hashes both
   before and after compression, decoded file hashes, and the off-device
   copies. Reuse modem firmware backups only if current full hashes match
   verified host copies. Stop on any unexplained read error or mismatch.
4. **Driver load / hardware hang risk:** on a fresh initramfs boot, prove
   modules are unlocked, GPU is not yet bound and the diagnostic gate is
   held. Start host logging and the bounded watchdog before the existing
   G1/G9 power sequence. Keep runtime PM forced on. Substitute only the
   SHA-verified G15 Panfrost module. Preserve the existing GPU core-ready
   gates. Stop on new faults, timeout, unexpected power state or USB loss.
5. **First draw / hardware hang risk:** before any compositor or other GPU
   client runs, use the private Mesa G10 GLES geometry probe. Require all
   768 pixels and no timeout/reset in the complete probe-to-draw kernel
   log. Capture MMU/job IRQ counters and time. Repeat the draw. A success
   after a recovery reset is a failure of this experiment's cold-start
   oracle, even if the final pixels match.
6. **User journey / visible change:** only after the first-draw gate,
   restore input30 and enter the GUI. Use the existing temporary G14 Mesa
   override with its timed rollback. Confirm the real driver/library
   mappings and ask the user to open Files and an Agent terminal. Repeat
   after a fresh boot before enabling persistent startup.

## Rollback and limits

On a pre-GUI failure, stop GPU clients, unload Panfrost before restoring
GPU supply, and use the existing G9 rollback under the watchdog. Do not
blindly unload a provider with users. If the kernel cannot respond, let
the watchdog recover; use Fastboot to select the known Linux images if
retries run out. A new boot removes RAM-only drivers and runtime overrides.
Do not flash G15 into startup or mark the whole device ready merely because
a module compiled or registered. Persistent B-success marking, touch/GPU
startup, thermal behavior, Wi-Fi, SIM and camera remain separate gates.


## Second-boot recovery after W2

First draw on the second kernel boot passed in0.127s; two repeats passed in
0.031/0.032s, each verifying768pixels. This was a new kernel boot, not a claim
of battery removal or a full thermal test. Input30 remained ready for60s.

GUI handoff replaced the serial shell and the old completion marker was lost.
A fresh connection confirmed systemd, SDDM and the touch/GPU modules. Newly
created `/var/tmp/oriole-g15` disappeared across handoff; cause remains unknown.
`/var/tmp` uses the same ext4 mount as root and its visible tmpfiles rule is30d,
so neither a separate mount nor an explicit per-boot delete was established.

The reviewed runtime scripts are now preserved in `gpu-g15-w2-runtime/` and
stage to `/opt/oriole-experiments/g15-w2-desktop`. Their manifest verifies exact
bytes. Run the bounded post-handoff GLES preflight before activation; never
substitute old-boot geometry logs to satisfy that check. Activation still uses
a90s rollback timer and180s watchdog, and requires immediate fresh-connection
confirmation before cancelling either. The change is runtime-only and does
not make GPU/boot/touch activation automatic.

The current Hyprland uses Lua dispatch syntax. Legacy `hyprctl dispatch dpms
on` returned exit7 (Lua parse error). In the active desktop user's session,
`hyprctl dispatch 'hl.dsp.dpms({ action = "enable" })'` succeeded; the following
grim capture showed the Omarchy menu and bottom navigation. A screenshot
while DPMS was off had timed out. Do not infer touch wake or physical panel
behavior from a compositor screenshot alone.
