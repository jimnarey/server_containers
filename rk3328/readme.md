## Build

```
docker build -t $(basename $(pwd)) .

```

## Run the container


```
docker run -v=$(basename $(pwd))-home:/home/runuser -v=/home/dockerman/rk3328_buildroot:/buildroot_root -e USERID=1002 -e GROUPID=1002 --name=$(basename $(pwd))-c $(basename $(pwd))
```