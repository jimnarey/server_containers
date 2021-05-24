# Double Commander

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run



```
docker run --volume=double-commander-home:/data --volume=/mnt:/host_volumes --publish=8081:8081 double-commander
```

* Based on ubuntu-wine-base

* Adds an additional volume to hold clrmamepro app and config files

* Sets the app to start via wine in supervisord.conf


