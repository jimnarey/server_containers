FROM base-ubuntu:latest

RUN mkdir -p /opt/dropbox 
WORKDIR /opt/dropbox
RUN wget -O dropbox.tar.gz "https://www.dropbox.com/download?plat=lnx.x86_64" && \
    tar -xzf dropbox.tar.gz && \
    wget -O dropbox.py https://www.dropbox.com/download?dl=packages/dropbox.py && \
    chmod +x dropbox.py && \
    chown -R runuser:runuser /opt/dropbox

RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 libglapi-mesa libxext-dev libxdamage-dev libxcb-glx0-dev libxcb-dri2-0-dev libxcb-dri3-dev \
    libxcb-present-dev libxshmfence-dev libxxf86vm-dev libqt5x11extras5 && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN echo "\nln -s /opt/dropbox/.dropbox-dist /home/runuser/.dropbox-dist\n" >> /usr/local/bin/init_chowns.sh

RUN mkdir /home/runuser/Dropbox

# RUN echo \
# '\n[program:app]\n\
# priority=1\n\
# environment=USER=runuser\n\
# command=/opt/dropbox/dropbox.py start\n\
# autorestart=true\n\
# stdout_logfile=/dev/fd/1\n\
# stdout_logfile_maxbytes=0\n\
# redirect_stderr=true\n'\
# >> /etc/supervisord.conf
