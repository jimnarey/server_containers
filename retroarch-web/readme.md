# Retoarch Web (Emscipten Build)

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -v=retroarch-web-home:/home/runuser -p=8082:8081 -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID retroarch-web
```

* Based on ubuntu-wine-base

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

* Sets the app to start via wine in supervisord.conf


