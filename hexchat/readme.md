# HexChat

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run


```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -p=$HEXCHAT_PORT:8081 -e USERID=$BASIC_ID -e GROUPID=$BASIC_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```


* Sets the app to start in supervisord.conf


