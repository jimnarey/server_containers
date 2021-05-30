#!/bin/bash
# Taken from linuxserver.io ubuntu base Dockerfile

USERID=${USERID:-1000}
GROUPID=${GROUPID:-1000}

groupmod -o -g "$GROUPID" app
usermod -o -u "$USERID" app

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
GROUPID/USERID
-----------------------------'
echo "
User uid:    $(id -u app)
User gid:    $(id -g app)
-----------------------------
"
/usr/local/bin/init_chowns.sh

exec gosu app supervisord