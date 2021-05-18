# Docker Extendable Image for Ubuntu-based Single GUI App over VNC

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t guiapp-base .

docker volume create guiapp-base-volume
```

## Run the container

For trying out and debugging:

```
docker run  --publish=8081:8081 guiapp-base
```

For production:

Something based on this:

```
docker run --detach --restart=always  --publish=8081:8081 guiapp-base
```

## Notes

* Uses Ubuntu in place of Debian to allow install of playonlinux via apt if needed.

* Changed line in (OpenBox's) rc.xml to point to correct menu location. Also see commented
out option for dealing with this in Dockerfile.

