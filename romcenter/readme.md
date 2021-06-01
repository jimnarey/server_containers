# Romcenter 

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the romcenter app which stores data in the same folder as the executable.

```
docker run -v=romcenter-home:/home/runuser -v=romcenter-app:/app  -p=8081:8081 -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID romcenter
```

Generic style:

```
docker run -v=$(basename $(pwd))-home:/home/runuser -v=$(basename $(pwd))-app:/app -p=8081:8081 -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold romcenter app and config files

* Sets the app to start via wine in supervisord.conf


