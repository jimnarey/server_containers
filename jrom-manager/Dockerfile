FROM base-ubuntu-gui-24:latest

WORKDIR /home/runuser
RUN wget https://github.com/optyfr/JRomManager/releases/download/3.0.5/jrommanager_3.0.5-1_amd64.deb -O jrommanager_3.0.5-1_amd64.deb

RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 libglapi-mesa libxext-dev libxdamage-dev libxcb-glx0-dev libxcb-dri2-0-dev libxcb-dri3-dev \
    libxcb-present-dev libxshmfence-dev libxxf86vm-dev libqt5x11extras5 nautilus

# JromManager fail to install without this
RUN mkdir -p /usr/share/desktop-directories

RUN apt-get update
RUN apt-get install -y --no-install-recommends ./jrommanager_3.0.5-1_amd64.deb
    
RUN apt-get clean -y && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/opt/jrommanager/bin/JRomManager\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/JRom Manager/g' /etc/supervisord.conf
