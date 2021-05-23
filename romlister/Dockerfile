FROM ubuntu-wine-base:latest

RUN mkdir /app && \
    wget -P /app https://www.waste.org/~winkles/ROMLister/RomLister.zip
WORKDIR /app
RUN unzip RomLister.zip && \
    chown -R app:app /app && \
    rm -f RomLister.zip
VOLUME /app

RUN echo \
'\nchown app:app /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/wine /app/RomLister.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
