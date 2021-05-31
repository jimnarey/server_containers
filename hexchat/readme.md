# HexChat

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run


```
docker run --volume=hexchat-home:/data --publish=8085:8081 hexchat
```


* Sets the app to start via wine in supervisord.conf


