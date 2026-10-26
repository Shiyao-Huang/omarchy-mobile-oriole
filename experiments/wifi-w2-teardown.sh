# SPDX-License-Identifier: MIT
# Sourced by the trial; operations are supplied by that trial.
# Never remove the PCI host while the endpoint or its driver is live.
wifi_w2_teardown() {
    wifi_endpoint_unbind || return 1
    wifi_endpoint_unbound || return 1
    wifi_radio_unload || return 1
    wifi_host_unload || return 1
    wifi_phy_unload || return 1
    wifi_rail_off || return 1
}
