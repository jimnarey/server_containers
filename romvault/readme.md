# Docker Wine RomVault

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the romvault app which stores data in the same folder as the executable.

```
docker run -v=romvault-home:/home/runuser -v=romvault-app:/app  -p=8081:8081 -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID romvault
```

Mount the necessary host dirs in the container:

```
docker run -v=romvault-home:/home/runuser -v=romvault-app:/app -e USERID=$RETRO_ID -e GROUPID=$RETRO_ID romvault
```

