FROM ubuntu-gui-base:latest

COPY Caddyfile /etc/

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
# CHANNGE APP NAME HERE\n\
command=/usr/bin/x-terminal-emulator\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

