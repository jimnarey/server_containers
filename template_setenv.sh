#!/bin/bash

## Runtime mount paths

# Cloud Backup

export IDRIVE_BACKUP_ROOT=
export IDRIVE_RESTORE_ROOT=
export IDRIVE_SERVICE_ROOT=
export IDRIVE_PROFILE_NAME=
export IDRIVE_CONTAINER_HOSTNAME=

export MEGANZ_SYNC_ROOT=

export DROPBOX_FOLDER=

# Rom Management

export ROM_ROOT=
export DAT_ROOT=
export ROM_OUTPUT=

# eBooks

export CALIBRE_LIBRARY=
export CALIBRE_SOURCE=

# Media

export VIDEO_ROOT=
export MUSIC_ROOT=
export PICTURES_ROOT=

# Documents

export DOCS_ROOT=

# Postgres Admin Credentials

POSTGRES_USER=postgres
POSTGRES_PASSWORD=

# Volume backup mount path

export VOLUME_BACKUP_DIR=

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
export OPENKM_PORTA=8088
export OPENKM_PORTB=8089
export TRANSMISSION_PORT=8090
export PS2TOOLS_PORT=9092
export CLRMAMEPRO_PORT=8093
export SIMPLE_ARCADE_MULTIFILTER_PORT=8094

export CADDY_HASH=

export TRANSMISSION_PASSWORD=
