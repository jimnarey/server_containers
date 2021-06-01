#!/bin/bash

source ../setenv.sh
RUN_IMAGE_NAME=$(basename $(pwd))
docker run -d -v=$RUN_IMAGE_NAME-home:/home/runuser -v=/mnt:/host_volumes -p=$DC_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID --name=$RUN_IMAGE_NAME-c $RUN_IMAGE_NAME