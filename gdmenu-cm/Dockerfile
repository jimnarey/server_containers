FROM base-ubuntu-gui:latest

# https://mamedev.emulab.it/clrmamepro/binaries/cmp4045_32.zip

# The application is extracted to a volume because it stores data in the same dir

RUN mkdir /app && \
    wget -P /app https://github.com/sonik-br/GDMENUCardManager/releases/download/v2.0.0/GDMENUCardManager.v2.0.0-linux-x64.tar.gz
WORKDIR /app
RUN tar -xf GDMENUCardManager.v2.0.0-linux-x64.tar.gz
RUN rm -f /app/gdmenucm/GDMENUCardManager.v2.0.0-linux-x64.tar.gz
RUN chown -R runuser:runuser /app

VOLUME /app

RUN echo \
'\nchown -R runuser:runuser /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:GDMENUCardManager]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/app/GDMENUCardManager\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /dreamcast_isos

RUN sed -i 's/Ubuntu GUI App Base Img/Dreamcast GDEMU Tools/g' /etc/supervisord.conf
