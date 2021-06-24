# Dropbox

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

```
docker run -d -v=$DROPBOX_FOLDER:/home/runuser/Dropbox --name=$(basename $(pwd))-c $(basename $(pwd))
```

