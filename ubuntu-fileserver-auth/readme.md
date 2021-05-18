# Basic template with fileserver and authentication

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t basic-auth .

docker volume create basic-auth-volume
```

## Get a password hash to pass to the container when it runs

```
docker run --rm -it basic-auth caddy hash-password --algorithm bcrypt

```

Copy the hash into the Caddyfile and specify a username:

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

As normal.

## Notes

* As ubuntu-gui-base but with Caddy fileserver and basic authentication enabled.



