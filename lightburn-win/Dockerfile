FROM lightburn-win-install:latest

ARG DEBIAN_FRONTEND=noninteractive

RUN sed -i 's|command=x-terminal-emulator -e "/home/runuser/install.sh"|command=/usr/bin/wine "/home/runuser/.wine/drive_c/Program Files/LightBurn/LightBurn.exe"|' /etc/supervisord.conf

RUN sed -i 's/autorestart=false/autorestart=true/' /etc/supervisord.conf

# f2fe2b8b-55f6-4044-b1c2-65b387abb3c7