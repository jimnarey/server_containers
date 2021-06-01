#!/bin/bash

source ../setenv.sh
RUN_IMAGE_NAME=$(basename $(pwd))
docker run -d -v=$RUN_IMAGE_NAME-home:/data -v=/mnt:/host_volumes -p=$DC_PORT:8081 -e USERID=$FILES_ID -e GROUPID=$FILES_ID $RUN_IMAGE_NAME