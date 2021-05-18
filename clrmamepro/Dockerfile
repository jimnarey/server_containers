FROM ubuntu-wine-mono:latest

RUN mkdir /clrmamepro && \
    wget -P /clrmamepro https://mamedev.emulab.it/clrmamepro/binaries/cmp4041_64.zip
WORKDIR /clrmamepro
RUN unzip cmp4041_64.zip && \
    chown -R app:app /clrmamepro && \
    rm -f cmp4041_64.zip
VOLUME /clrmamepro

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/wine /clrmamepro/cmpro64.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
