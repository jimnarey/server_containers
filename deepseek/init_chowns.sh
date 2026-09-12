#!/bin/bash
set -e

chown runuser:runuser /home/runuser
# The profile overlays are read-only bind mounts from this repository. Chown
# all other persisted DSH state, but prune that directory so a safe overlay
# cannot abort container startup before /dev/stdout is made writable.
find /home/runuser -mindepth 1 -maxdepth 1 \
    ! -name .ssh \
    ! -name .dsh \
    -exec chown -R runuser:runuser {} +

if [ -d /home/runuser/.dsh ]; then
    find /home/runuser/.dsh \
        -path /home/runuser/.dsh/profiles -prune -o \
        -exec chown runuser:runuser {} +
fi

chown runuser:runuser /dev/stdout
