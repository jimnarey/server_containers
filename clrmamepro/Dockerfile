FROM ubuntu-wine-base:latest

RUN mkdir /app && \
    wget -P /app https://mamedev.emulab.it/clrmamepro/binaries/cmp4041_64.zip
WORKDIR /app
RUN unzip cmp4041_64.zip && \
    chown -R app:app /app && \
    rm -f cmp4041_64.zip
VOLUME /app

RUN echo \
'\nchown app:app /app\n' \
>> /usr/local/bin/setids.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/wine /app/cmpro64.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
