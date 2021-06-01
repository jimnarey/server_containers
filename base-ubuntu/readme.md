# Docker Extendable Ubuntu Image

The most basic image, setting up supervisord and a few other bits.


## Build

```
docker build -t $(basename $(pwd)) .

```


## Run the container

Basic:

```
docker run -p=8081:8081 base-ubuntu
```

Pass the desired UID and GID for the user which runs the container's apps:

```
docker run -v=base-ubuntu-home:/data -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID base-ubuntu
```


Consider --detach and --restart-always.

## Notes

* Initially used in place of Debian due to ease of getting PlayOnLinux from the repos, though it turned out to be easier to use Wine itself.


