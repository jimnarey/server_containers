# IDrive

## Note

Unlike other images this needs setenv.sh to be sourced before build, not just before run.

It then needs the account_settings.pl script to be run and configured from within the container, once running:

```
docker exec -u runuser -it $(basename $(pwd))-c /bin/bash
```

## Build

```
docker build -t $(basename $(pwd)) --build-arg IDRIVE_PROFILE_NAME=$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$IDRIVE_SERVICE_ROOT .
```

## Run

Generic:

```
docker run -d -v=$(basename $(pwd))-home:/home/$IDRIVE_PROFILE_NAME -v=$IDRIVE_BACKUP_ROOT:$IDRIVE_BACKUP_ROOT -v=$IDRIVE_RESTORE_ROOT:$IDRIVE_RESTORE_ROOT -v=$IDRIVE_SERVICE_ROOT:$IDRIVE_SERVICE_ROOT --hostname=$IDRIVE_CONTAINER_HOSTNAME --name=$(basename $(pwd))-c $(basename $(pwd))

```

