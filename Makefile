SHELL := /bin/bash

EXT_VOLUMES_MAPPING := $(shell ./get_ext_volumes_map.sh nas runuser)

build-sources:
	docker build -t build-caddy ./build-caddy
	docker build -t build-easy-novnc ./build-easy-novnc
	docker build -t download-retroarch-emscripten ./download-retroarch-emscripten

build-bases:
	docker build -t base-ubuntu ./base-ubuntu
	docker build --no-cache -t base-ubuntu-22 ./base-ubuntu-22
	docker build --no-cache -t base-ubuntu-24 ./base-ubuntu-24
	docker build -t base-ubuntu-caddy ./base-ubuntu-caddy
	docker build -t base-ubuntu-caddy-22 ./base-ubuntu-caddy-22
	docker build -t base-ubuntu-gui ./base-ubuntu-gui
	docker build -t base-ubuntu-gui-22 ./base-ubuntu-gui-22
	docker build -t base-ubuntu-wine ./base-ubuntu-wine

build-calibre:
	docker build -t calibre ./calibre

run-calibre: build-calibre
	source env.sh && docker run -d -v=calibre-home:/home/runuser -v=/$$CALIBRE_LIBRARY:/library -v=/$$CALIBRE_SOURCE:/source -p=$$CALIBRE_PORT:8081 -p=$$CALIBRE_WEB_PORT:8083 -e USERID=$$FILES_ID -e CADDY_HASH=$$CADDY_HASH -e GROUPID=$$FILES_ID --name=calibre-c calibre

build-clrmamepro:
	docker build -t clrmamepro ./clrmamepro

run-clrmamepro: build-clrmamepro
	source ./env.sh && docker run -d -v=clrmamepro-home:/home/runuser -v=clrmamepro-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$CLRMAMEPRO_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=clrmamepro-c clrmamepro

build-double-commander:
	docker build -t double-commander ./double-commander

run-double-commander:
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

run-double-commander-root:
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

build-dropbox:
	docker build -t dropbox ./dropbox

run-dropbox: build-dropbox
	source env.sh && docker run -d -v dropbox-home:/home/runuser -v=$$DROPBOX_FOLDER:/home/runuser/Dropbox --name=dropbox-c dropbox

run-dropbox: build-dropbox
	source env.sh && docker run -d -v=$$DROPBOX_FOLDER:/home/runuser/Dropbox --name=dropbox-c dropbox

build-dropbox-src:
	docker build -t dropbox-src ./dropbox-src

run-dropbox-src: build-dropbox-src
	source env.sh && docker run -d -v dropbox-src-home:/home/runuser -v=$$DROPBOX_FOLDER:/home/runuser/Dropbox --name=dropbox-src-c dropbox-src

build-dropbox-gui:
	docker build -t dropbox-gui ./dropbox-gui

run-dropbox-gui: build-dropbox-gui
	source env.sh && docker run -d -v dropbox-gui-home:/home/runuser -v=$$DROPBOX_FOLDER:/home/runuser/Dropbox -e CADDY_HASH=$$CADDY_HASH -p=$$DROPBOX_GUI_PORT:8081 --name=dropbox-gui-c dropbox-gui

build-filezilla:
	docker build -t filezilla ./filezilla

run-filezilla: build-filezilla
	source env.sh && docker run -d -v=filezilla-home:/home/runuser -v=/mnt:/host_volumes -p=$$FILEZILLA_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=filezilla-c filezilla

build-gdmenu-cm:
	docker build -t gdmenu-cm ./gdmenu-cm

run-gdmenu-cm: build-gdmenu-cm
	source env.sh && docker run -d -v=gdmenu-cm-home:/home/runuser -v=build-gdmenu-cm-app:/app -v=$$DREAMCAST_ISO_DIR:/dreamcast_isos $(EXT_VOLUMES_MAPPING) -p=$$GDMENU_CM_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=gdmenu-cm-c gdmenu-cm

build-hexchat:
	docker build -t hexchat ./hexchat

run-hexchat: build-hexchat
	source env.sh && docker run -d -v=hexchat-home:/home/runuser -p=$$HEXCHAT_PORT:8081 -e USERID=$$BASIC_ID -e GROUPID=$$BASIC_ID --name=hexchat-c hexchat

build-idrive:
	source env.sh && docker build -t idrive --build-arg IDRIVE_PROFILE_NAME=$$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$$IDRIVE_SERVICE_ROOT ./idrive

build-lightburn:
	docker build -t lightburn ./lightburn

run-lightburn: build-lightburn
	source env.sh && docker run -d -v=lightburn-home:/home/runuser -v=$$LIGHTBURN_ROOT:/lightburn -p=$$LIGHTBURN_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=basic -e CADDY_HASH=$$LIGHTBURN_CADDY_HASH --name=lightburn-c lightburn

build-meganz:
	docker build -t meganz ./meganz

run-meganz: build-meganz
	source env.sh && docker run -d -v=meganz-home:/home/runuser -v=/mnt:/host_mnt --name=meganz-c meganz

build-mindnla:
	docker build -t minidnla ./minidnla

run-minidnla: build-minidnla
	source env.sh && docker run -d -v=minidnla-home:/home/runuser -v=$$VIDEO_ROOT:/video:ro -v=$$MUSIC_ROOT:/music:ro -v=$$PICTURES_ROOT:/pictures:ro --network=host -e USERID=$$MEDIA_ID -e GROUPID=$$MEDIA_ID --name=minidnla-c minidnla

build-nkit:
	docker build -t nkit ./nkit

run-nkit:
	source ./env.sh && docker run -d -v=nkit-home:/home/runuser -v=nkit-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$NKIT_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=nkit-c nkit

build-ps2tools:
	docker build -t ps2tools ./ps2tools

run-ps2tools: build ps2tools
	source env.sh && docker run -d -v=ps2tools-home:/home/runuser -v=/mnt:/host_mnt -v=/media:/host_media -p=$$PS2TOOLS_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=ps2tools-c ps2tools

build-retroarch-web:
	docker build -t retroarch-web ./retroarch-web

run-retroarch-web: build-retroarch-web
	source env.sh && docker run -v=retroarch-web-home:/home/runuser -p=8082:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=retroarch-web-c retroarch-web

build-simple-arcade-multifilter:
	docker build -t simple-arcade-multifilter ./simple-arcade-multifilter

run-simple-arcade-multifilter: build-simple-arcade-multifilter
	source env.sh && docker run -d -v=simple-arcade-multifilter-home:/home/runuser -v=simple-arcade-multifilter-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$SIMPLE_ARCADE_MULTIFILTER_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=simple-arcade-multifilter-c simple-arcade-multifilter

build-transmission:
	source env.sh && docker build -t transmission --build-arg TRANSMISSION_PASSWORD=$$TRANSMISSION_PASSWORD  ./transmission

run-transmission: build-transmission
	source env.sh && docker run -d -v=transmission-home:/home/runuser -v=/mnt:/host_volumes -p=9091:9091 -p=51413:51413 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=transmission-c transmission

run-transmission-vpn:
	source env.sh && env BUILDKIT_PROGRESS=plain docker compose -f transmission-vpn.yml up -d

down-transmission-vpn:
	docker compose -f transmission-vpn.yml down
