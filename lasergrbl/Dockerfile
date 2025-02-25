FROM lasergrbl-install:latest

ARG DEBIAN_FRONTEND=noninteractive

RUN sed -i 's|command=x-terminal-emulator -e "/home/runuser/install.sh"|command=wine /home/runuser/.wine/drive_c/Program\\ Files/LaserGRBL/LaserGRBL.exe|' /etc/supervisord.conf

RUN sed -i 's/autorestart=false/autorestart=true/' /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/LaserGRBL/g' /etc/supervisord.conf

