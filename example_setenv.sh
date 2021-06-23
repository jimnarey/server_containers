#!/bin/bash

## Runtime mount paths

# Cloud Backup

export IDRIVE_BACKUP_ROOT
export IDRIVE_RESTORE_ROOT
export IDRIVE_SERVICE_ROOT

# Rom Management

export ROM_ROOT
export DAT_ROOT
export ROM_OUTPUT
#export DREAMCAST_ISO=/mnt/int_data_a/Retro/Roms/dreamcast

# eBooks

export CALIBRE_LIBRARY
export CALIBRE_SOURCE

# Media

export VIDEO_ROOT
export MUSIC_ROOT
export PICTURES_ROOT

# Documents

export DOCS_ROOT

# Volume backup mount path

export VOLUME_BACKUP_DIR

# UID/GID for the users which will run containers' main apps

export FILES_ID
export RETRO_ID
export BOOKS_ID
export BASIC_ID
export MEDIA_ID

# Port assignment for apps

export CALIBRE_PORT
export CALIBRE_WEB_PORT
export HEXCHAT_PORT
export DOUBLE_CMDR_PORT
export FILEZILLA_PORT
export XFBURN_PORT
