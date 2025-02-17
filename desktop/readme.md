# Double Commander

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

As standard user:

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/mnt:/host_volumes -p=$DOUBLE_CMDR_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=admin -e CADDY_HASH=$CADDY_HASH --name=$(basename $(pwd))-c $(basename $(pwd))
```

As root:

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/mnt:/host_volumes -p=$DOUBLE_CMDR_PORT:8081 -e USERID=0 -e GROUPID=0 -e CADDY_USER=admin -e CADDY_HASH=$CADDY_HASH --name=$(basename $(pwd))-c $(basename $(pwd))
```

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

