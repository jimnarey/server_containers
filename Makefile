SHELL := /bin/bash

# EXT_VOLUMES_MAPPING := $(shell ./get_ext_volumes_map.sh "/media/fileman" runuser)

EXT_VOLUMES_MAPPING := $(shell ./get_ext_volumes_map_old.sh fileman runuser)

build-sources:
	docker build -t build-caddy ./build-caddy
	docker build -t build-easy-novnc ./build-easy-novnc
	docker build -t download-retroarch-emscripten ./download-retroarch-emscripten

build-ubuntu:
	docker build --no-cache -t base-ubuntu ./base-ubuntu

build-bases:
	docker build -t base-ubuntu-caddy ./base-ubuntu-caddy
	docker build -t base-ubuntu-gui ./base-ubuntu-gui
	docker build -t base-ubuntu-wine ./base-ubuntu-wine

build-calibre: build-bases
	docker build -t calibre ./calibre

run-calibre: build-calibre
	source env.sh && docker run -d -v=calibre-home:/home/runuser -v=/$$CALIBRE_LIBRARY:/library -v=/$$CALIBRE_SOURCE:/source -p=$$CALIBRE_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=calibre-c calibre

build-clrmamepro: build-bases
	docker build -t clrmamepro ./clrmamepro
 
run-clrmamepro: build-clrmamepro
	source ./env.sh && docker run -d -v=clrmamepro-home:/home/runuser -v=clrmamepro-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$CLRMAMEPRO_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=calibre-c-c clrmamepro

build-double-commnder: build-bases
	docker build -t double-commnder ./double-commnder

run-double-commander: build-double-commander
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

run-double-commander-root: build-double-commander
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

build-dropbox: build-bases
	docker build -t dropbox ./dropbox

run-dropbox: build-dropbox
	source env.sh && docker run -d -v=$$DROPBOX_FOLDER:/home/runuser/Dropbox --name=dropbox-c dropbox

start-dropbox-sync:
	docker exec -u runuser -it dropbox-c /opt/dropbox/dropbox.py start

status-dropbox:
	docker exec -u runuser -it dropbox-c /opt/dropbox/dropbox.py status

build-filezilla: build-bases
	docker build -t filezilla ./filezilla

run-filezilla: build-filezilla
	source env.sh && docker run -d -v=filezilla-home:/home/runuser -v=/mnt:/host_volumes -p=$$FILEZILLA_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=filezilla-c filezilla

build-gdmenu-cm: build-bases
	docker build -t gdmenu-cm ./gdmenu-cm

run-gdmenu-cm: build-gdmenu-cm
# source env.sh
# EXT_VOLUMES=$(shell ./get_ext_volumes_map.sh $$FILES_ID)
	source env.sh && docker run -d -v=build-gdmenu-cm-home:/home/runuser -v=build-gdmenu-cm-apps:/apps -v=$$DREAMCAST_ISO_DIR:/dreamcast_isos $(EXT_VOLUMES_MAPPING) -p=$$GDMENU_CM_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=gdmenu-cm-c gdmenu-cm

build-hexchat: build-bases
	docker build -t hexchat ./hexchat

run-hexchat: build-hexchat
	source env.sh && docker run -d -v=hexchat-home:/home/runuser -p=$$HEXCHAT_PORT:8081 -e USERID=$$BASIC_ID -e GROUPID=$$BASIC_ID --name=hexchat-c hexchat

build-idrive: build-bases
	source env.sh && docker build -t idrive --build-arg IDRIVE_PROFILE_NAME=$$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$$IDRIVE_SERVICE_ROOT ./idrive

run-idrive: build-idrive
	source env.sh &&

build-meganz: build-bases
	docker build -t meganz ./meganz

run-meganz: build-meganz
	source env.sh && docker run -d -v=meganz-home:/home/runuser -v=/mnt:/host_mnt --name=meganz-c meganz

shell-mega-nz:
	docker exec -u runuser -it meganz-c /bin/bash

sync-status-meganz:
	docker exec -u runuser -it meganz-c mega-sync --path-display-size=150

transfers-status-meganz:
	docker exec -u runuser -it meganz-c mega-transfers --show-syncs --path-display-size=150

build-mindnla: build-bases
	docker build -t minidnla ./minidnla

run-minidnla: build-minidnla
	source env.sh && docker run -d -v=minidnla-home:/home/runuser -v=$$VIDEO_ROOT:/video:ro -v=$$MUSIC_ROOT:/music:ro -v=$$PICTURES_ROOT:/pictures:ro --network=host -e USERID=$$MEDIA_ID -e GROUPID=$$MEDIA_ID --name=minidnla-c minidnla

# build-openkm: build-bases
# 	source env.sh && docker build -t openkm-c --build-arg=PG_USERNAME="openkm" --build-arg=PG_PASSWORD=$$PG_PASSWORD --build-arg=PG_HOST="localhost" ./openkm

# run-openkm: build-openkm
# 	source env.sh && docker run -d -v=openkm-home:/home/runuser -p=$$OPENKM_PORTA:8080 -p=$$OPENKM_PORTB:2002  -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=openkm-c openkm

# build-postgres-custom: build-bases
# 	source env.sh && docker build -t postgres-custom --build-arg POSTGRES_USER=$$POSTGRES_USER --build-arg POSTGRES_PASSWORD=$$POSTGRES_PASSWORD ./postgres-custom

# run-postgres-custom: build-postgres-custom
# 	source env.sh && ??????????????????

build-ps2tools: build-bases
	docker build -t ps2tools ./ps2tools

run-ps2tools: build ps2tools
	source env.sh && docker run -d -v=ps2tools-home:/home/runuser -v=/mnt:/host_mnt -v=/media:/host_media -p=$$PS2TOOLS_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=ps2tools-c ps2tools

build-retroarch-web: build-bases
	docker build -t retroarch-web ./retroarch-web

run-retroarch-web: build-retroarch-web
	source env.sh && docker run -v=retroarch-web-home:/home/runuser -p=8082:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=retroarch-web-c retroarch-web

build-rk3328: build-bases
	docker build -t rk3328 ./rk3328

run-rk3328: build-rk3328
	source env.sh && docker run -v=rk3328-home:/home/runuser -v=/home/dockerman/rk3328_buildroot:/buildroot_root -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=rk3328-c rk3328

build-romcenter: build-bases
	docker build -t romcenter ./romcenter

run-romcenter: build-romcenter
	source env.sh && docker run -v=romcenter-home:/home/runuser -v=romcenter-app:/app -p=8081:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=romcenter-c romcenter

build-romlister: build-bases
	docker build -t romlister ./romlister

run-romlister: build-romlister
	source env.sh && docker run -v=romlister-home:/home/runuser -v=romlister-app:/app -p=8081:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=romlister-c romlister

# build-romulus: build-bases

build-romvault: build-bases
	docker build -t romvault ./romvault

# run-romvault: build-romvault
# 	source env.sh && ??????????????????????

build-simple-arcade-multifilter: build-bases
	docker build -t simple-arcade-multifilter ./simple-arcade-multifilter

run-simple-arcade-multifilter: build-simple-arcade-multifilter
	source env.sh && docker run -d -v=simple-arcade-multifilter-home:/home/runuser -v=simple-arcade-multifilter-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$SIMPLE_ARCADE_MULTIFILTER_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=simple-arcade-multifilter-c simple-arcade-multifilter

build-transmission: build-bases
	source env.sh && docker build -t transmission --build-arg TRANSMISSION_PASSWORD=$$TRANSMISSION_PASSWORD  ./transmission

run-transmission: build-transmission
	source env.sh && docker run -d -v=transmission-home:/home/runuser -v=/mnt:/host_volumes -p=9091:9091 -p=51413:51413 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID --name=transmission-c transmission

build-ugly-gdemu-gm: build-bases
	docker build -t ugly-gdemu-gm ./ugly-gdemu-gm

run-ugly-gdemu-gm: build-ugly-gdemu-gm
	source env.sh && docker run -d -v=ugly-gdemu-gm-home:/home/runuser -v=ugly-gdemu-gm-apps:/apps -v=$$DREAMCAST_ISO_DIR:/dreamcast_isos $(EXT_VOLUMES_MAPPING) -p=$$UGLY_GDEMU_GM_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=ugly-gdemu-gm-c ugly-gdemu-gm

# build-xfburn: build-bases
# 	docker build -t xfburn-c ./xfburn

test:
	# source env.sh
	# MOO := "hello"
	# MOO:=$(shell ./get_ext_volumes_map.sh fileman)
	@echo $(EXT_VOLUMES_MAPPING)