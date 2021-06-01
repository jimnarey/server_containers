#!/bin/bash

cd base-ubuntu
docker build -t $(basename $(pwd)) .

cd ../base-ubuntu-caddy
docker build -t $(basename $(pwd)) .

cd ../base-ubuntu-gui
docker build -t $(basename $(pwd)) .

cd ../base-ubuntu-wine
docker build -t $(basename $(pwd)) .
