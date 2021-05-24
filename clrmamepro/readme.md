# Docker, Wine, ClrMamePro

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the clrmamepro app which stores data in the same folder as the executable.

```
docker run --volume=clrmamepro-home:/data --volume=clrmamepro-app:/app  --publish=8081:8081 clrmamepro
```

Set the UID and GID for the container's user:

```
docker run --volume=clrmamepro-home:/data --volume=clrmamepro-app:/app  --publish=8081:8081 -e USERID=900 -e GROUPID=900 clrmamepro
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold clrmamepro app and config files

* Sets the app to start via wine in supervisord.conf


