# Xfburn

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -d -p=$XFBURN_PORT:8081 -v /dev:/dev -e USERID=0 -e GROUPID=0 xfburn
```

Generic:

```
docker run -d -p=$XFBURN_PORT:8081 -v=/dev:/dev --privileged -v=/mnt:/host_volumes -e USERID=0 -e GROUPID=0 --name=$(basename $(pwd))-c $(basename $(pwd))
```

