# Docker, Wine, Dreamcast/GDEMU Tools

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=$(basename $(pwd))-apps:/apps -v=$DREAMCAST_ISO_DIR:/dreamcast_isos -p=$GDMENU_CM_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$CADDY_HASH --name=$(basename $(pwd))-c $(basename $(pwd))
```

* Based on ubuntu-wine-base

* Adds an additional volume pointing to Dreamcast ISOs on host

* Sets the app to start via wine in supervisord.conf


