FROM base-ubuntu-gui-24:latest

WORKDIR /home/runuser

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-full python3-pip python3-lxml python3-gi python3-appdirs inkscape
    
RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

COPY blank.svg /home/runuser/

RUN echo \
'\n[program:inkscape]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/inkscape /home/runuser/blank.svg\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN mkdir /lasercutting

RUN sed -i 's/Ubuntu GUI App Base Img/Inkscape/g' /etc/supervisord.conf