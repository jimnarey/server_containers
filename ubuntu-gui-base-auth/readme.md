# Basic template with fileserver and authentication

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t ubuntu-gui-base-auth .

docker volume create ubuntu-gui-base-auth-volume
```

## Get a password hash to pass to the container when it runs

```
docker run --rm -it ubuntu-gui-base-auth caddy hash-password --algorithm bcrypt

```

Copy the hash into the Caddyfile:

```
:8081 {
    log
    reverse_proxy 127.0.0.1:8080
    basicauth /* {
        admin JDJhJDEwJEdoQTZxUmExdk15M2pNQUZYcUh1VnU4bXBYTks2eUZrYXUwamtjM2tZeEU2dEJEUi52Q3pp
    }
}
```

Or pass the hash as an environment variable:

```
:8081 {
    log
    reverse_proxy 127.0.0.1:8080
    basicauth /* {
        {env.APP_USERNAME} {env.APP_PASSWORD_HASH}
    }
}
```

Then run:

```
docker run --volume=polapp-volume:/data --env=APP_USERNAME="admin" --env=APP_PASSWORD_HASH="JDJhJDEwJEdoQTZxUmExdk15M2pNQUZYcUh1VnU4bXBYTks2eUZrYXUwamtjM2tZeEU2dEJEUi52Q3pp" --publish=8081:8081 ubuntu-gui-base-auth
```


## Notes

*Based on ubuntu-gui-base

*Use variation of Caddyfile to enable authentication. Default password is 'lamp'.