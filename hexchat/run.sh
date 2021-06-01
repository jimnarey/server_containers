#!/bin/bash

source ../setenv.sh
RUN_IMAGE_NAME=$(basename $(pwd))
docker run -d -v=$RUN_IMAGE_NAME-home:/data -p=$HEXCHAT_PORT:8081 -e USERID=$BASIC_ID -e GROUPID=$BASIC_ID $RUN_IMAGE_NAME