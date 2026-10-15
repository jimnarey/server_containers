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

# The web profile's providers and models are a read-only bind mount from this
# repository (deepseek/profile-patches/web.profile.cordis.patch.yml), so there is
# nothing to seed into a new home.
mkdir -p /home/runuser/.dsh
chown runuser:runuser /home/runuser/.dsh

chown runuser:runuser /dev/stdout
