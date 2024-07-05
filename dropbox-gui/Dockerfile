FROM base-ubuntu-gui-22:latest

WORKDIR /home/runuser
RUN wget https://www.dropbox.com/download?dl=packages/ubuntu/dropbox_2020.03.04_amd64.deb -O dropbox_2020.03.04_amd64.deb

RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 libglapi-mesa libxext-dev libxdamage-dev libxcb-glx0-dev libxcb-dri2-0-dev libxcb-dri3-dev \
    libxcb-present-dev libxshmfence-dev libxxf86vm-dev libqt5x11extras5 nautilus

RUN apt-get update
RUN apt-get install -y ./dropbox_2020.03.04_amd64.deb 
    
RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /home/runuser/Dropbox

WORKDIR /home/runuser/Dropbox

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=nautilus\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
