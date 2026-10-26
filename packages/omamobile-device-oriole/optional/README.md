# Oriole optional runtime profiles

These files are copied from the public Pixel 6 GS101 reference path and are
kept out of the default device package until a normal Omarchy boot has passed
the corresponding hardware gate. They contain no firmware, calibration or
credentials.

Reference: [pixel6-mainline-nura/device-google-oriole](https://github.com/TheNoswad/pixel6-mainline-nura/tree/a74e18dec7598f65cd504f0c75c10b8d7fc4422b/device/testing/device-google-oriole), whose device packaging is MIT licensed.

Apply one profile only after the matching gate is approved:

- `wifi/90-bcmdhd-unmanaged.conf` keeps Android-only BCM4389 interfaces out of
  NetworkManager. It does not associate with an access point.
- `camera/` exposes the system dma-buf heap to video users, hides raw CSIS
  nodes from WirePlumber, loads the camera heap module and leaves the known
  failing GN1 main sensor unbound. The front IMX355 and ultra-wide IMX386
  still require the GS101 kernel and libcamera patches.
- `performance/` limits the ACPM schedutil update rate and removes the Android
  real-time utilization floor. It does not enable the GPU or change voltages.

The profile files are inputs for the gated runbook; copying them into `/etc`
or enabling the service is a separate device operation and must be recorded
with its rollback.
