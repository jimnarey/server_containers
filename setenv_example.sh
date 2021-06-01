#!/bin/bash

# Runtime mount paths
export ROM_ROOT=/mnt/int_data_a/Retro/Roms
export DAT_ROOT=/mnt/int_data_a/Retro/DATs
export ROM_OUTPUT=/mnt/int_data_a/Retro/Output
export CALIBRE_LIBRARY=/mnt/int_data_b/CalibreLibrary
export CALIBRE_SOURCE=/mnt/ext_data_a/Cloud/Dropbox/Fiction

# Volume backup mount path

export VOLUME_BACKUP_DIR=/mnt/int_data_b/volume_backups

# UID/GID for the users which will run containers' main apps
export BOOKS_ID=1003
export BASIC_ID=1004
export RETRO_ID=1001
export FILES_ID=1000

# Port assignment for apps

export CALIBRE_PORT=8082
export HEXCHAT_PORT=8083
export DC_PORT=8084