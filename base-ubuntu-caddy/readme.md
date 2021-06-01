# Docker Extendable Ubuntu & Caddy Image

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t $(basename $(pwd)) .

```

## Get a password hash

Caddy uses a password hash which is provided via environment variable CADDY_HASH or defaults to the hash for 'password' (default username is 'admin'). To get a hash for your desired password, run:

```
docker run --rm -it base-ubuntu-caddy caddy hash-password --algorithm bcrypt
```

## Run the container

Basic:

```
docker run  -p=8081:8081 base-ubuntu-caddy
```

Pass the desired UID and GID for the user which runs the container's apps:

```
docker run -v=base-home:/data -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID base-ubuntu-caddy
```

Pass in the UID/GID and Caddy credentials (includes the hash for 'caddy'):

```
docker run -v=base-home:/data -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID -e CADDY_USER=caddy -e CADDY_HASH=JDJhJDEwJGF2emhqVGM4RERVQ2dQb2NOOEdiQWVEd2htNjRFSDlVOUJJTWlZNmNPdmRNZnlnT1lLTTBD base-ubuntu-caddy
```


Consider --detach and --restart-always:

```
docker run --detach --restart=always  -p=8081:8081 base-ubuntu-caddy
```

## Notes

* Uses Ubuntu in place of Debian to allow install of playonlinux via apt if needed.

