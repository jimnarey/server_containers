#!/bin/bash

# Taken from linuxserver.io ubuntu base Dockerfile

PUID=${PUID:-1000}
PGID=${PGID:-1000}

groupmod -o -g "$PGID" app
usermod -o -u "$PUID" app

echo '
----------------------------
      ____               
     /___/\_             
    _\   \/_/\__         
  __\       \/_/\        
  \   __    __ \ \       
 __\  \_\   \_\ \ \   __ 
/_/\\   __   __  \ \_/_/\
\_\/_\__\/\__\/\__\/_\_\/
   \_\/_/\       /_\_\/  
      \_\/       \_\/     

-----------------------------

-----------------------------
GID/UID
-----------------------------'
echo "
User uid:    $(id -u app)
User gid:    $(id -g app)
-----------------------------
"
chown app:app /data
# chown app:app /app

# Read additional dirs in from vars