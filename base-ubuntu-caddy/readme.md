# Docker Extendable Ubuntu & Caddy Image

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Parent

See readme for base-ubuntu.

## Get a password hash

Caddy uses a password hash which is provided via environment variable CADDY_HASH or defaults to the hash for 'password' (default username is 'admin'). To get a hash for your desired password, run:

```
docker run --rm -it base-ubuntu-caddy caddy hash-password --algorithm bcrypt
```

## Run the container

Basic:

Pass in the UID/GID and Caddy credentials (includes the hash for 'caddy'):

```
docker run -v=base-home:/home/runuser -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=caddy -e CADDY_HASH=JDJhJDEwJGF2emhqVGM4RERVQ2dQb2NOOEdiQWVEd2htNjRFSDlVOUJJTWlZNmNPdmRNZnlnT1lLTTBD base-ubuntu-caddy
```

Generic style:

```
docker run -v=$(basename $(pwd))-home:/home/runuser -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=caddy -e CADDY_HASH=JDJhJDEwJGF2emhqVGM4RERVQ2dQb2NOOEdiQWVEd2htNjRFSDlVOUJJTWlZNmNPdmRNZnlnT1lLTTBD --name=$(basename $(pwd))-c $(basename $(pwd))
```

