# Docker Wine App Notepad++ Example

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the clrmamepro app which stores data in the same folder as the executable.

```
docker run --volume=clrmamepro-home:/data --volume=clrmamepro-app:/clrmamepro  --publish=8081:8081 clrmamepro
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold clrmamepro app and config files

* Sets the app to start via wine in supervisord.conf


