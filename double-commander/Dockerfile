FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends doublecmd-gtk && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists


RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/doublecmd /host_volumes /host_volumes\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN sed -i 's/Ubuntu GUI App Base Img/Double Commander/g' /etc/supervisord.conf


