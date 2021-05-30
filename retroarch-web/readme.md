# Retoarch Web (Emscipten Build)

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run



```
docker run --volume=retroarch-web-home:/data --publish=8082:8081 retroarch-web
```

* Based on ubuntu-wine-base

* Mounts the host's /mnt dir as /host_volumes in the container and points double commander there on start

* Sets the app to start via wine in supervisord.conf


