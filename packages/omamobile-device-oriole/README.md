# Pixel 6 first-light device package

Experimental oriole package adapted from the upstream conservative felix package. It stages shared storage protection, USB networking and reboot-to. No boot-success, charger, radio, camera or PMIC service is enabled. Display refresh was verified separately on GS101; full Arch/Omarchy userspace and touch remain untested.

The descriptor is pinned to the locally tested Android 16 firmware baseline. A host-side installer must validate device and firmware before using it. Software reboot-to bootloader did not reliably enter fastboot on this Pixel 6.
