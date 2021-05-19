# Docker Wine App Notepad++ Example

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the romlister app which stores data in the same folder as the executable.

```
docker run --volume=romlister-home:/data --volume=romlister-app:/app  --publish=8081:8081 romlister
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold romlister app and config files

* Sets the app to start via wine in supervisord.conf


