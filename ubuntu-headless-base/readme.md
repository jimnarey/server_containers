# Docker Extendable Ubuntu & Caddy Image

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t ubuntu-headless-base .

docker volume create ubuntu-headless-base-volume
```

## Get a password hash

Caddy uses a password hash which is provided via environment variable CADDY_HASH or defaults to the hash for 'password' (default username is 'admin'). To get a hash for your desired password, run:

```
docker run --rm -it ubuntu-headless-base caddy hash-password --algorithm bcrypt
```

## Run the container

Basic:

```
docker run  --publish=8081:8081 ubuntu-headless-base
```

Pass the desired UID and GID for the user which runs the container's apps:

```
docker run --volume=base-home:/data --publish=8081:8081 -e USERID=900 -e GROUPID=900 ubuntu-headless-base
```

Pass in the UID/GID and Caddy credentials (includes the hash for 'caddy'):

```
docker run --volume=base-home:/data --publish=8081:8081 -e USERID=900 -e GROUPID=900 -e CADDY_USER=caddy -e CADDY_HASH=JDJhJDEwJGF2emhqVGM4RERVQ2dQb2NOOEdiQWVEd2htNjRFSDlVOUJJTWlZNmNPdmRNZnlnT1lLTTBD ubuntu-headless-base
```


Consider --detach and --restart-always:

```
docker run --detach --restart=always  --publish=8081:8081 ubuntu-headless-base
```

## Notes

* Uses Ubuntu in place of Debian to allow install of playonlinux via apt if needed.


