# IDrive

## Notes

Unlike other images this needs setenv.sh to be sourced before build, not just before run.

It then needs the account_settings.pl script to be run and configured from within the container, once running:

```
docker exec -u runuser -it $(basename $(pwd))-c /bin/bash
```

There's quite a lot of stuff in the Dockerfile aimed at, as far as possible, duplicating the environement on the host machine (user, paths) so that an iDrive setup running on a Linux box can be transferred into a container without iDrive treating it as a new/separate backup source. Some of it could be pruned if this isn't the case and it's possible that matching the usernames isn't actually needed if it is the case.

So there's some room for refinement/simplification with this one. Not helped by the iDrive Linux docs not being amazing and some of the way it works being a bit opaque. Nobody on technical support could give me a clear explanation as to what purpose the 'profile' in the iDrive web interface has (the profile name is automatically generated from the Linux username running the scripts).

## Build

```
docker build -t $(basename $(pwd)) --build-arg IDRIVE_PROFILE_NAME=$IDRIVE_PROFILE_NAME --build-arg IDRIVE_BACKUP_ROOT=$IDRIVE_BACKUP_ROOT --build-arg IDRIVE_RESTORE_ROOT=$IDRIVE_RESTORE_ROOT --build-arg IDRIVE_SERVICE_ROOT=$IDRIVE_SERVICE_ROOT .
```

## Run

```
docker run -d -v=$(basename $(pwd))-home:/home/$IDRIVE_PROFILE_NAME -v=$IDRIVE_BACKUP_ROOT:$IDRIVE_BACKUP_ROOT -v=$IDRIVE_RESTORE_ROOT:$IDRIVE_RESTORE_ROOT -v=$IDRIVE_SERVICE_ROOT:$IDRIVE_SERVICE_ROOT --hostname=$IDRIVE_CONTAINER_HOSTNAME --name=$(basename $(pwd))-c $(basename $(pwd))

```

```
docker exec -u fileman -it idrive-c /opt/idrive/IDriveForLinux/scripts/account_setting.pl
```
