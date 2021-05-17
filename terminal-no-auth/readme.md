# Docker Terminal & Basic Authentication App Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t terminal .

docker volume create terminal-volume
```

## Run the container

For trying out and debugging:

```
docker run --volume=terminal-volume:/data --name=terminal-c --publish=8081:8081 terminal
```

For production:

Something based on this:

```
docker run --detach --restart=always --volume=terminal-volume:/data --name=terminal-c --publish=8081:8081 terminal
```

*Uses Ubuntu in place of Debian to get playonlinux via apt.

*Switched the version of Go to just numbered (not sure if this makes a difference?)

*Specified the timezone in Dockerfile to avoid a hang on build.

*Specified the app user as an environment variable for PlayOnLinux

*Changed line in (OpenBox's) rc.xml to point to correct menu location. Also see commented
out option for dealing with this in Dockerfile

