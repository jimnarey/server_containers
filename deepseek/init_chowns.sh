#!/bin/bash
set -e

chown runuser:runuser /home/runuser
find /home/runuser -mindepth 1 -maxdepth 1 ! -name .ssh -exec chown -R runuser:runuser {} +
chown runuser:runuser /dev/stdout
