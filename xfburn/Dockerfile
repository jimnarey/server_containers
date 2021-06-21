FROM base-ubuntu-gui:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends xfburn && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/xfburn\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN sed -i 's/Ubuntu GUI App Base Img/Gparted/g' /etc/supervisord.conf
