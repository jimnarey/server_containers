#!/bin/bash

## Runtime mount paths

# Cloud Backup

export IDRIVE_BACKUP_ROOT=/mnt/ext_data_a/Cloud/iDrive
export IDRIVE_RESTORE_ROOT=/mnt/ext_data_a/Cloud/iDriveRestore
export IDRIVE_SERVICE_ROOT=/mnt/ext_data_a/Cloud/iDriveService
export IDRIVE_PROFILE_NAME=fileman
export IDRIVE_CONTAINER_HOSTNAME=nas

# Rom Management

export ROM_ROOT=/mnt/int_data_a/Retro/Roms
export DAT_ROOT=/mnt/int_data_a/Retro/DATs
export ROM_OUTPUT=/mnt/int_data_a/Retro/Output
#export DREAMCAST_ISO=/mnt/int_data_a/Retro/Roms/dreamcast

# eBooks

export CALIBRE_LIBRARY=/mnt/int_data_b/CalibreLibrary
export CALIBRE_SOURCE=/mnt/ext_data_a/Cloud/Dropbox/Fiction

# Media

export VIDEO_ROOT=/mnt/int_data_b/Video
export MUSIC_ROOT=/mnt/ext_data_a/Cloud/Dropbox/Music
export PICTURES_ROOT=/home/dockerman/empty

# Documents

export DOCS_ROOT=/mnt/int_data_b/DocumentLibrary

# Volume backup mount path

export VOLUME_BACKUP_DIR=/mnt/int_data_b/volume_backups

# UID/GID for the users which will run containers' main apps

export FILES_ID=1000
export RETRO_ID=1001
export BOOKS_ID=1003
export BASIC_ID=1004
export MEDIA_ID=$BASIC_ID

# Port assignment for apps

export CALIBRE_PORT=8082
export CALIBRE_WEB_PORT=8083
export HEXCHAT_PORT=8084
export DOUBLE_CMDR_PORT=8085
export FILEZILLA_PORT=8086
export XFBURN_PORT=8087
