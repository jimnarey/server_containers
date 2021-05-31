# Double Commander

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run --volume=double-commander-home:/data --volume=/mnt:/host_volumes --publish=8081:8081 double-commander
```

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

* Sets the app to start via wine in supervisord.conf


