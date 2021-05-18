# Docker PlayOnLinux App Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

```
docker build -t polapp .

docker volume create polapp-volume
```

## Get a password hash to pass to the container when it runs

```
docker run --rm -it polapp caddy hash-password --algorithm bcrypt

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

Or pass the hash as an environment variable: [NEED TO TEST!]

```
:8081 {
    log
    reverse_proxy 127.0.0.1:8080
    basicauth /* {
        {env.APP_USERNAME} {env.APP_PASSWORD_HASH}
    }
}
```


## Run the container

For trying out and debugging:

(with the login credentials in the Caddyfile)

```
docker run --volume=polapp-volume:/data --name=playonlinux-app --publish=8081:8081 polapp
```

For production:

Something based on this:

```
docker run --detach --restart=always --volume=polapp-volume:/data --name=playonlinux-app --env=APP_USERNAME="myuser" --env=APP_PASSWORD_HASH="mypass-hash" --publish=8081:8081 polapp
```

*Uses Ubuntu in place of Debian to get playonlinux via apt.

*Switched the version of Go to just numbered (not sure if this makes a difference?)

*Specified the timezone in Dockerfile to avoid a hang on build.

*Specified the app user as an environment variable for PlayOnLinux

*Changed line in (OpenBox's) rc.xml to point to correct menu location. Also see commented
out option for dealing with this in Dockerfile

*Includes basic authentication with a password hash set in the Caddyfile. See passhash.sh for
generating password hash.

*WIP:

docker run --detach --restart=always --volume=thunderbird-data:/data --net=thunderbird-net --name=thunderbird-web --env=APP_USERNAME="myuser" --env=APP_PASSWORD_HASH="mypass-hash" --publish=8080:8080 thunderbird-caddy

...and the credentials passed in as variables:

```
docker run --volume=polapp-volume:/data --name=playonlinux-app --env=APP_USERNAME="myuser" --env=APP_PASSWORD_HASH="mypass-hash" --publish=8081:8081 polapp
```

