FROM base-ubuntu-wine-24:latest

RUN mkdir /app && \
    wget -P /app https://github.com/markwkidd/ahk-retroarch-playlist-helpers/releases/download/v1.22/Simple.Arcade.Multifilterv1.22_2019-01-09.exe
WORKDIR /app
VOLUME /app

RUN echo \
'\nchown -R runuser:runuser /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/Simple.Arcade.Multifilterv1.22_2019-01-09.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_mnt && \
    mkdir /host_media

RUN sed -i 's/Ubuntu GUI App Base Img/Simple Arcade Multifilter/g' /etc/supervisord.conf
