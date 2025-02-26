# Filezilla

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -v=filezilla-home:/home/runuser -v=/mnt:/host_volumes -p=$DC_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID filezilla
```

Generic:

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/mnt:/host_volumes -p=$FILEZILLA_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

* Sets the app to start via wine in supervisord.conf


