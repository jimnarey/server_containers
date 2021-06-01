# Docker Calibre Template

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

```
docker run -v=calibre-home:/data -p=8081:8081 -e USERID=1000 -e GROUPID=1000 calibre
```

```
docker run -d -v=calibre-home:/data -v=/$CALIBRE_LIBRARY:/library -v=/$CALIBRE_SOURCE:/source -p=$CALIBRE_PORT:8081 -e USERID=$BOOKS_ID -e GROUPID=$BOOKS_ID calibre
```


* Based on ubuntu-gui-base


