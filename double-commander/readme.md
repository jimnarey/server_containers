# Double Commander

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -v=double-commander-home:/data -v=/mnt:/host_volumes -p=$DC_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID double-commander
```

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

* Sets the app to start via wine in supervisord.conf


