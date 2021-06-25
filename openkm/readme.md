# Docker Extendable Ubuntu & Caddy Image

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9



*********
## Get a password hash

See base-ubuntu-caddy
*********


## Build

docker build -t $(basename $(pwd)) --build-arg=PG_USERNAME="openkm" --build-arg=PG_PASSWORD="secret" --build-arg=PG_HOST="localhost" .

## Run the container

Basic:

*******
With the default username/password:
********

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -p=$OPENKM_PORTA:8080 -p=$OPENKM_PORTB:2002  -e USERID=$BOOKS_ID -e GROUPID=$BOOKS_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```


Pass in the UID/GID and Caddy credentials (includes the hash for 'caddy'):

```
docker run -v=$(basename $(pwd))-home:/home/runuser -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=caddy -e CADDY_HASH=JDJhJDEwJGF2emhqVGM4RERVQ2dQb2NOOEdiQWVEd2htNjRFSDlVOUJJTWlZNmNPdmRNZnlnT1lLTTBD --name=$(basename $(pwd))-c $(basename $(pwd))
```

## 

docker build -t my-openkm --build-arg=PG_USERNAME="openkm" --build-arg=PG_PASSWORD="secret" --build-arg=PG_HOST="localhost" .

This example needs a simple dockerfile in the current directory containing only one line:

FROM mmuellerm/openkm-debian-pg

After building the image you can create your container:

docker create --name openkm -p 8080:8080 my-openkm

This example requires a host with name "postgres-host" and a running postgres instance. It must contains a database 'okmdb' and a database user "openkm" with password "secret" with full access rights to the database 'okmdb'.