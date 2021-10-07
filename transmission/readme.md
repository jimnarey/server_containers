# Transmission

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9


## Build

docker build -t $(basename $(pwd)) --build-arg TRANSMISSION_PASSWORD=$TRANSMISSION_PASSWORD  .

## Run


```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/mnt:/host_volumes -p=9091:9091 -p=51413:51413 -e USERID=$FILES_ID -e GROUPID=$FILES_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```




