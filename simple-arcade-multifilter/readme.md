# Docker, Wine, Simple Arcade Multifilter

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the app which stores data in the same folder as the executable.

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=$(basename $(pwd))-app:/app -v=/mnt:/host_mnt -v=/media:/host_media -p=$SIMPLE_ARCADE_MULTIFILTER_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$CADDY_HASH --name=$(basename $(pwd))-c $(basename $(pwd))
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold clrmamepro app and config files

* Sets the app to start via wine in supervisord.conf


