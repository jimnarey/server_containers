# Mega.nz Command Line Tools

## Notes

Unlike other images this needs setenv.sh to be sourced before build, not just before run.

It then needs the XXXXXXX script to be run and configured from within the container, once running:

```
docker exec -u runuser -it $(basename $(pwd))-c /bin/bash
```

## Build

```
docker build -t $(basename $(pwd)) .
```

## Run

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/mnt:/host_mnt --name=$(basename $(pwd))-c $(basename $(pwd))

```

