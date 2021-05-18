FROM ubuntu-wine-base:latest

# RUN apt-get install xz-utils

RUN mkdir -p /tmp/mono
RUN wget -P /tmp/mono https://dl.winehq.org/wine/wine-mono/6.1.1/wine-mono-6.1.1-x86.tar.xz
WORKDIR /tmp/mono
RUN tar -xJf wine-mono-6.1.1-x86.tar.xz
RUN ls -la
RUN mkdir -p /usr/share/wine/mono
# RUN mv wine-mono-6.1.1 /usr/share/wine/mono


RUN mkdir -p /usr/share/clrmamepro
RUN wget -P /usr/share/clrmamepro https://mamedev.emulab.it/clrmamepro/binaries/cmp4041_64.zip
WORKDIR /usr/share/clrmamepro
RUN unzip cmp4041_64.zip
RUN chown -R app:app /usr/share/clrmamepro

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/wine /usr/share/clrmamepro/cmpro64.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
