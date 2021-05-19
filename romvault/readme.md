# Docker Wine App Notepad++ Example

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the romvault app which stores data in the same folder as the executable.

```
docker run --volume=romvault-home:/data --volume=romvault-app:/app  --publish=8081:8081 romvault
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold romvault app and config files

* Sets the app to start via wine in supervisord.conf


