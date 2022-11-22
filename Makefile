SHELL := /bin/bash

build-sources:
	docker build -t build-caddy ./build-caddy
	docker build -t build-easy-novnc ./build-easy-novnc
	docker build -t download-retroarch-emscripten

build-ubuntu:
	docker build --no-cache -t base-ubuntu ./base-ubuntu

build-bases:
	docker build -t base-ubuntu-caddy ./base-ubuntu-caddy
	docker build -t base-ubuntu-gui ./base-ubuntu-gui
	docker build -t base-ubuntu-wine ./base-ubuntu-wine

build-calibre: build-bases
	docker build -t calibre-c ./calibre

build-clrmamepro: build-bases
	docker build -t clrmamepro-c ./clrmamepro

build-double-commnder: build-bases
	docker build -t double-commnder-c ./double-commnder

build-dropbox: build-bases
	docker build -t dropbox-c ./dropbox

build-filezilla: build-bases
	docker build -t filezilla-c ./filezilla

build-gdmenu-cm: build-bases
	docker build -t gdmenu-cm-c ./gdmenu-cm

build-hexchat: build-bases
	docker build -t hexchat-c ./hexchat

build-idrive: build-bases
	source env.sh && docker build -t idrive-c --build-arg IDRIVE_PROFILE_NAME=$$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$$IDRIVE_SERVICE_ROOT ./idrive

build-meganz: build-bases
	docker build -t meganz-c ./meganz

build-mindnla: build-bases
	docker build -t minidnla-c ./minidnla

# build-openkm: build-bases
# 	source env.sh && docker build -t openkm-c --build-arg=PG_USERNAME="openkm" --build-arg=PG_PASSWORD=$$PG_PASSWORD --build-arg=PG_HOST="localhost" ./openkm

# build-postgres-custom: build-bases
# 	source env.sh && docker build -t $(basename $(pwd)) --build-arg POSTGRES_USER=$$POSTGRES_USER --build-arg POSTGRES_PASSWORD=$$POSTGRES_PASSWORD ./postgres-custom

build-ps2tools: build-bases
	docker build -t ps2tools-c ./ps2tools

build-retroarch-web: build-bases
	docker build -t retroarch-web-c ./retroarch-web

build-rk3328: build-bases
	docker build -t rk3328-c ./rk3328

build-romcenter: build-bases
	docker build -t romcenter-c ./romcenter

build-romlister: build-bases
	docker build -t romlister-c ./romlister

# build-romulus: build-bases

build-romvault: build-bases
	docker build -t romvault-c ./romvault

build-simple-arcade-multifilter: build-bases
	docker build -t simple-arcade-multifilter-c ./simple-arcade-multifilter

build-transmission: build-bases
	source env.sh && docker build -t transmission-c --build-arg TRANSMISSION_PASSWORD=$$TRANSMISSION_PASSWORD  ./transmission

build-ugly-gdemu-gm: build-bases
	docker build -t ugly-gdemu-gm-c ./ugly-gdemu-cm-c

# build-xfburn: build-bases
# 	docker build -t xfburn-c ./xfburn

