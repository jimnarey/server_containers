# Docker Gerbera

## Run

```
docker run -d -v=gerbera-home:/home/runuser -e USERID=$MEDIA_ID -e GROUPID=$MEDIA_ID gerbera
```

Generic style:

```
docker run -d -v=$(basename $(pwd))-home:/home/runuser -v=$VIDEO_ROOT:/video:ro -v=$MUSIC_ROOT:/music:ro -v=$PICTURES_ROOT:/pictures:ro -p=8200:8200 -e USERID=$MEDIA_ID -e GROUPID=$MEDIA_ID --name=$(basename $(pwd))-c $(basename $(pwd))
```

## Notes

* Based on base-ubuntu