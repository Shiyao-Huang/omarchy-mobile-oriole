#!/bin/sh
# Local override for Agent terminals only; original launcher stays untouched.
# Keep network/install failures readable until the user closes the window.
if [ "${1-}" = '--app-id=org.omarchy.agent' ]; then
    shift
    exec setsid uwsm-app -- xdg-terminal-exec --hold --app-id=org.omarchy.agent -e "$@"
fi
exec /usr/bin/omarchy-launch-tui "$@"
