FROM base-ubuntu-wine:latest

# https://mamedev.emulab.it/clrmamepro/binaries/cmp4045_32.zip

# The application is extracted to a volume because it stores data in the same dir

RUN mkdir /app && \
    wget -P /app https://github.com/Louhike/Ugly-GDEmu-Games-Manager/releases/download/Version_0_7_3/UGGM_0_7_3_SELFCONTAINED.zip

WORKDIR /app
RUN unzip UGGM_0_7_3_SELFCONTAINED.zip

RUN rm -f /app/UGGM_0_7_3_SELFCONTAINED.zip

RUN chown -R runuser:runuser /app

VOLUME /apps

RUN echo \
'\nchown -R runuser:runuser /apps\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:UglyGDEMUGamesManager]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/GDEmuSdCardManager.exe\n\
autorestart=true\n\ 
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\n'\
>> /etc/supervisord.conf

RUN mkdir /dreamcast_isos

RUN sed -i 's/Ubuntu GUI App Base Img/Ugly GDEMU Games Manager/g' /etc/supervisord.conf
