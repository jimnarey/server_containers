SHELL := /bin/bash

EXT_VOLUMES_MAPPING := $(shell ./get_ext_volumes_map.sh nas runuser)

build-sources:
	docker build -t download-retroarch-emscripten ./download-retroarch-emscripten

build-bases:
	docker build --no-cache -t base-ubuntu-24 ./base-ubuntu-24
	docker build -t base-ubuntu-caddy-24 ./base-ubuntu-caddy-24
	docker build -t base-ubuntu-gui-24 ./base-ubuntu-gui-24
	docker build -t base-ubuntu-wine-24 ./base-ubuntu-wine-24
	docker build -t base-ubuntu-kde-24 ./base-ubuntu-kde-24
	docker build -t base-ubuntu-kde-wine-24 ./base-ubuntu-kde-wine-24

build-old-bases:
	docker build --no-cache -t base-ubuntu-22 ./base-ubuntu-22
	docker build -t base-ubuntu-caddy-22 ./base-ubuntu-caddy-22
	docker build -t base-ubuntu-gui-22 ./base-ubuntu-gui-22
	docker build --no-cache -t base-ubuntu ./base-ubuntu
	docker build -t base-ubuntu-caddy ./base-ubuntu-caddy
	docker build -t base-ubuntu-gui ./base-ubuntu-gui

run-base-ubuntu-kde-24:
	source env.sh && docker run -d -v=/mnt:/host_volumes -p=$$DESKTOP_KDE_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=base-ubuntu-kde-24-c base-ubuntu-kde-24

build-calibre:
	docker build -t calibre ./calibre

run-calibre: build-calibre
	source env.sh && docker run -d -v=calibre-home:/home/runuser -v=/$$CALIBRE_LIBRARY:/library -v=/$$CALIBRE_SOURCE:/source -p=$$CALIBRE_PORT:8081 -p=$$CALIBRE_WEB_PORT:8083 -e USERID=$$FILES_ID -e CADDY_HASH=$$CADDY_HASH -e GROUPID=$$FILES_ID --name=calibre-c calibre

build-clrmamepro:
	docker build -t clrmamepro ./clrmamepro

run-clrmamepro: build-clrmamepro
	source ./env.sh && docker run -d -v=clrmamepro-home:/home/runuser -v=clrmamepro-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$CLRMAMEPRO_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=clrmamepro-c clrmamepro

build-document-viewers:
	docker build -t document-viewers ./document-viewers

run-document-viewers:
	source env.sh && docker run -d -v=document-viewers-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOC_VIEWERS_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=document-viewers-c document-viewers

build-double-commander:
	docker build -t double-commander ./double-commander

run-double-commander:
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

run-double-commander-root:
	source env.sh && docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c docker run -d -v=double-commander-home:/home/runuser -v=/mnt:/host_volumes -p=$$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=double-commander-c double-commander

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
	source env.sh && docker run -d -v=gdmenu-cm-home:/home/runuser -v=build-gdmenu-cm-app:/app -v=/mnt:/host_volumes $(EXT_VOLUMES_MAPPING)  -p=$$GDMENU_CM_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=gdmenu-cm-c gdmenu-cm

build-hexchat:
	docker build -t hexchat ./hexchat

run-hexchat: build-hexchat
	source env.sh && docker run -d -v=hexchat-home:/home/runuser -p=$$HEXCHAT_PORT:8081 -e USERID=$$BASIC_ID -e GROUPID=$$BASIC_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=hexchat-c hexchat

build-idrive:
	source env.sh && docker build -t idrive --build-arg IDRIVE_PROFILE_NAME=$$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$$IDRIVE_SERVICE_ROOT ./idrive

build-laserweb:
	docker build -t laserweb ./laserweb

run-laserweb:
	source env.sh && docker run -d -v=laserweb-home:/home/runuser --device $$LASERCUTTER_DEV -v=$$LASER_CUTTING_ROOT:/lasercutting -p=$$LASERWEB_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=laserweb-c laserweb

build-lightburn:
	docker build -t lightburn ./lightburn

run-lightburn-priv:
	source env.sh && docker run -d --privileged -v=/dev:/dev -v=lightburn-home:/home/runuser -v="$$LASER_CUTTING_ROOT":/lasercutting -p=$$LIGHTBURN_PORT:8081 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=lightburn-c lightburn 

build-lasergrbl-install:
	docker build -t lasergrbl-install lasergrbl-install

build-lasergrbl:
	docker build -t lasergrbl lasergrbl

run-lasergrbl-install: build-lasergrbl-install
	source env.sh && docker run --rm -d --privileged -v=/dev:/dev -v=lasergrbl-home:/home/runuser -p=$$LASERGRBL_PORT:8081 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=lasergrbl-install-c lasergrbl-install

run-lasergrbl: build-lasergrbl
	source env.sh && docker run -d --privileged -v=/dev:/dev -v=lasergrbl-home:/home/runuser -v="$$LASER_CUTTING_ROOT":/lasercutting -p=$$LASERGRBL_PORT:8081 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=lasergrbl-c lasergrbl

build-meganz:
	docker build -t meganz ./meganz

run-meganz: build-meganz
	source env.sh && docker run -d -v=meganz-home:/home/runuser -v=/mnt:/host_mnt --name=meganz-c meganz

build-nkit:
	docker build -t nkit ./nkit

run-nkit:
	source ./env.sh && docker run -d -v=nkit-home:/home/runuser -v=nkit-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$$NKIT_PORT:8081 -e USERID=$$FILES_ID -e GROUPID=$$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=nkit-c nkit

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

build-inkscape-visicut:
	docker build -t inkscape-visicut ./inkscape-visicut

run-inkscape-visicut-priv:
	source env.sh && docker run -d --privileged -v=/dev:/dev -v=inkscape-visicut-home:/home/runuser -v="$$LASER_CUTTING_ROOT":/lasercutting -p=$$INKSCAPE_VISICUT_PORT:8081 -e CADDY_USER=admin -e CADDY_HASH=$$CADDY_HASH --name=inkscape-visicut-c inkscape-visicut 


# run-lightburn-priv:
# 	source env.sh && \
# 	TEMP_SPOOF_DIR=$$(mktemp -d) && \
# 	echo "$$(uuidgen)" > $$TEMP_SPOOF_DIR/machine-id && \
# 	echo "$$(uuidgen)" > $$TEMP_SPOOF_DIR/product_uuid && \
# 	RANDOM_MAC=$$(printf '02:42:%02x:%02x:%02x:%02x' $$(shuf -i 0-255 -n1) $$(shuf -i 0-255 -n1) $$(shuf -i 0-255 -n1) $$(shuf -i 0-255 -n1)) && \
# 	SPOOFED_HOSTNAME="lightburn-$$(shuf -i 1000-9999 -n1)" && \
# 	mkdir -p $$TEMP_SPOOF_DIR/sys/class/block && \
# 	for dev in /sys/class/block/*; do \
# 		DEV_NAME=$$(basename $$dev); \
# 		if [[ $$DEV_NAME != loop* ]]; then \
# 			echo "$$(uuidgen)" > $$TEMP_SPOOF_DIR/sys/class/block/$$DEV_NAME; \
# 		fi \
# 	done && \
# 	sudo mount --bind $$TEMP_SPOOF_DIR/sys/class/block /sys/class/block && \
# 	TEMP_DEV=$$(mktemp -d) && \
# 	(test -e /dev/ttyUSB* && cp -r /dev/ttyUSB* $$TEMP_DEV/) || true && \
# 	(test -e /dev/ttyACM* && cp -r /dev/ttyACM* $$TEMP_DEV/) || true && \
# 	sudo cp -r /dev/null $$TEMP_DEV/ && \
# 	sudo cp -r /dev/zero $$TEMP_DEV/ && \
# 	sudo ln -s /dev/null $$TEMP_DEV/stdout && \
# 	sudo ln -s /dev/null $$TEMP_DEV/stderr && \
# 	sudo ln -s /dev/tty && \
# 	sudo ln -s /dev/stdin $$TEMP_DEV/fd/0 && \
# 	sudo ln -s /dev/stdout $$TEMP_DEV/fd/1 && \
# 	sudo ln -s /dev/stderr $$TEMP_DEV/fd/2 && \
# 	docker run -d --privileged \
# 		--mount type=bind,source=$$TEMP_DEV,target=/dev,bind-propagation=rslave \
# 		-v=lightburn-home:/home/runuser \
# 		-v="$$LASER_CUTTING_ROOT":/lasercutting \
# 		-v=$$TEMP_SPOOF_DIR/machine-id:/etc/machine-id:ro \
# 		-v=$$TEMP_SPOOF_DIR/product_uuid:/sys/class/dmi/id/product_uuid:ro \
# 		--mount type=bind,source=$$TEMP_SPOOF_DIR/sys/class/block,target=/sys/class/block,bind-propagation=rslave \
# 		-h $$SPOOFED_HOSTNAME \
# 		-p=$$LIGHTBURN_PORT:8081 \
# 		-e CADDY_USER=admin \
# 		-e CADDY_HASH=$$CADDY_HASH \
# 		--mac-address=$$RANDOM_MAC \
# 		--name=lightburn-c lightburn
