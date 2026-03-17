#!/bin/bash

docker compose build --no-cache base-ubuntu-22
docker compose build --no-cache base-ubuntu-caddy-22
docker compose build --no-cache base-ubuntu-gui-22
docker compose build --no-cache base-ubuntu-24
docker compose build --no-cache base-ubuntu-caddy-24
docker compose build --no-cache base-ubuntu-gui-24
docker compose build --no-cache base-ubuntu-kde-24
docker compose build --no-cache base-ubuntu-kde-wine-24
docker compose build --no-cache base-ubuntu-wine-24
docker compose build --no-cache base-ubuntu-xfce-22
docker compose build --no-cache base-ubuntu-xfce-24
