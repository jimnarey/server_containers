FROM ubuntu-gui-base:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends hexchat && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists


RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/hexchat\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/HexChat/g' /etc/supervisord.conf
