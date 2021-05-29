# Docker Wine RomVault

https://www.digitalocean.com/community/tutorials/how-to-remotely-access-gui-applications-using-docker-and-caddy-on-debian-9

## Run

Needs an additional volume to hold the romvault app which stores data in the same folder as the executable.

```
docker run --volume=romvault-home:/data --volume=romvault-app:/app  --publish=8081:8081 romvault
```

Mount the necessary host dirs in the container:

```
docker run --volume=romvault-home:/data --volume=romvault-app:/app --volume=$ROM_ROOT:/rom_root --volume=$DAT_ROOT:/dat_root --volume=$ROM_OUTPUT:/rom_output --publish=8081:8081 -e USERID=1001 -e GROUPID=1001 romvault
```

