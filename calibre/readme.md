# Docker Calibre

## Run

```
docker run -d -v=calibre-home:/home/runuser -v=/$CALIBRE_LIBRARY:/library -v=/$CALIBRE_SOURCE:/source -p=$CALIBRE_PORT:8081 -e USERID=$BOOKS_ID -e GROUPID=$BOOKS_ID calibre
```

Generic style:

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=/$CALIBRE_LIBRARY:/library -v=/$CALIBRE_SOURCE:/source -p=$CALIBRE_PORT:8081 -e USERID=$BOOKS_ID -e GROUPID=$BOOKS_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```

## Notes

* Based on base-ubuntu-gui


