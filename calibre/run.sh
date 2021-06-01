#!/bin/bash

source ../setenv.sh
RUN_IMAGE_NAME=$(basename $(pwd))
docker run -d -v=$RUN_IMAGE_NAME-home:/data -v=/$CALIBRE_LIBRARY:/library -v=/$CALIBRE_SOURCE:/source -p=$CALIBRE_PORT:8081 -e USERID=$BOOKS_ID -e GROUPID=$BOOKS_ID $RUN_IMAGE_NAME