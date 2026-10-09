#!/bin/bash
set -e

chown runuser:runuser /home/runuser
# The headless profile overlay is a read-only bind mount from this repository.
# Chown all other persisted DSH state, but prune profiles so that overlay cannot
# abort container startup before /dev/stdout is made writable.
find /home/runuser -mindepth 1 -maxdepth 1 \
    ! -name .ssh \
    ! -name .dsh \
    -exec chown -R runuser:runuser {} +

if [ -d /home/runuser/.dsh ]; then
    find /home/runuser/.dsh \
        -path /home/runuser/.dsh/profiles -prune -o \
        -path /home/runuser/.dsh/settings.yaml -prune -o \
        -exec chown runuser:runuser {} +
fi

# DSH 0.2 migrates the legacy document to the writable web profile. Seed it
# only for a genuinely new home; an imported backup is the durable sentinel
# that prevents a later container recreation from overwriting user settings.
mkdir -p /home/runuser/.dsh
chown runuser:runuser /home/runuser/.dsh
if [ ! -e /home/runuser/.dsh/settings.yaml ] && \
   [ ! -e /home/runuser/.dsh/settings.yaml.imported ] && \
   [ ! -e /home/runuser/.dsh/profiles/web/cordis.patch.yml ]; then
    install -o runuser -g runuser -m 600 \
        /opt/dsh/default-settings.yaml /home/runuser/.dsh/settings.yaml
fi

chown runuser:runuser /dev/stdout
