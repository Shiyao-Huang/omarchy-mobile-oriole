# SPDX-License-Identifier: MIT
"""Read-only decoder of gs-common devinfo3.15 boot flags; never writes."""
import struct

def decode(data):
    if len(data) != 128:
        raise ValueError("Expected exactly128 header bytes")
    magic, major, minor = struct.unpack_from("<IHH", data)
    if magic != 0x49564544 or (major, minor) != (3, 15):
        raise ValueError("Unverified header layout")
    slots = {}
    for name, offset in (("a", 0x30), ("b", 0x34)):
        retry, flags, reserved0, reserved1 = data[offset:offset+4]
        slots[name] = dict(retry_count=retry, unbootable=bool(flags & 1),
                           successful=bool(flags & 2), active=bool(flags & 4),
                           fastboot_ok=bool(flags & 8),
                           reserved_nonzero=bool((flags & 0xf0) or reserved0 or reserved1))
    return dict(version="3.15", slots=slots)
