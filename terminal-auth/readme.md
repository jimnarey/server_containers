# Docker Terminal & Basic Authentication App Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t terminal .

docker volume create terminal-volume
```

## Get a password hash to pass to the container when it runs

```
docker run --rm -it terminal caddy hash-password --algorithm bcrypt

```

Copy this into the Caddyfile:

```
:8081 {
    log
    reverse_proxy 127.0.0.1:8080
    basicauth /* {
        admin JDJhJDEwJEt5aHVFY0IvbUEwWVpScUVvYjFSZi5kSGVkdWtYL3pCWGFqVmd0TXF5Qk83TXFrMnVBUEFP
    }
}
```


## Run the container

For trying out and debugging:

(with the login credentials in the Caddyfile)

```
docker run --volume=terminal-volume:/data --name=terminal-c --publish=8081:8081 terminal
```

For production:

Something based on this:

```
docker run --detach --restart=always --volume=terminal-volume:/data --name=terminal-c --publish=8081:8081 terminal
```

*As terminal-no-auth but with Caddy basic authentication enabled.

*Changed line in (OpenBox's) rc.xml to point to correct menu location. Also see commented
out option for dealing with this in Dockerfile

