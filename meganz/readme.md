# Mega.nz Command Line Tools

## Notes

Unlike other images this needs setenv.sh to be sourced before build, not just before run.

It then needs the XXXXXXX script to be run and configured from within the container, once running:

```
docker exec -u runuser -it $(basename $(pwd))-c /bin/bash
```

## Build

```
docker build -t $(basename $(pwd)) --build-arg MEGANZ_SYNC_A=$MEGANZ_SYNC_A --build-arg MEGA_SYNC_B=$MEGA_SYNC_B  .
```

## Run

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=$MEGANZ_SYNC_A:$MEGANZ_SYNC_A -v=$MEGANZ_SYNC_B:$MEGANZ_SYNC_B --name=$(basename $(pwd))-c $(basename $(pwd))

```

