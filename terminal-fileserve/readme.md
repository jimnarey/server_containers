# Docker Terminal, Fileserver & Basic Authentication App Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t terminal-fs .

docker volume create terminal-fs-volume
```

## Run the container

For trying out and debugging:

```
docker run --volume=terminal-fs-volume:/data --publish=8081:8081 terminal-fs
```

For production:

Something based on this:

```
docker run --detach --restart=always --volume=terminal-fs-volume:/data --publish=8081:8081 terminal-fs
```

*Based on terminal-no-auth

*Enabled fileserver function in Caddy