# Docker, Wine, ClrMamePro

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the clrmamepro app which stores data in the same folder as the executable.

```
docker run -v=clrmamepro-home:/data -v=clrmamepro-app:/app  -p=8081:8081 clrmamepro
```

Set the UID and GID for the container's user:

```
docker run -v=clrmamepro-home:/data -v=clrmamepro-app:/app  -p=8081:8081 -e USERID=900 -e GROUPID=900 clrmamepro
```

Mount the necessary host dirs in the container:

```
docker run -v=clrmamepro-home:/data -v=clrmamepro-app:/app -v=$ROM_ROOT:/rom_root -v=$DAT_ROOT:/dat_root -v=$ROM_OUTPUT:/rom_output -p=8081:8081 -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID clrmamepro
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold clrmamepro app and config files

* Sets the app to start via wine in supervisord.conf


