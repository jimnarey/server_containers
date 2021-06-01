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

The built image has a user created within it ('runuser') which is essential to managing the permissions for anything run in the container, otherwise everything runs as root. The UID/GID for runuser can be set when the container starts:

```
docker run -v=base-ubuntu-home:/home/runuser -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID base-ubuntu
```

Generic style:

```
docker run -v=$(basename $(pwd))-home:/home/runuser -p=8081:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```

Consider --detach and --restart-always.

## Backup Home Dir Volume

```
docker run --rm --volumes-from $(basename $(pwd))-c -v $VOLUME_BACKUP_DIR:/backup base-ubuntu tar cvf /backup/backup.tar /home/runuser
```


## Notes

* Initially used in place of Debian due to ease of getting PlayOnLinux from the repos, though it turned out to be easier to use Wine itself.


