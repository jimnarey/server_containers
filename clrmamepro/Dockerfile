FROM base-ubuntu-wine:latest

# https://mamedev.emulab.it/clrmamepro/binaries/cmp4045_32.zip

# The application is extracted to a volume because it stores data in the same dir
RUN mkdir /app && \
    wget -P /app https://mamedev.emulab.it/clrmamepro/binaries/cmp4045_32.zip 
WORKDIR /app
RUN unzip cmp4045_32.zip && \
    chown -R runuser:runuser /app && \
    rm -f cmp4045_32.zip
VOLUME /app

RUN echo \
'\nchown -R runuser:runuser /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/cmpro.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_mnt && \
    mkdir /host_media

RUN sed -i 's/Ubuntu GUI App Base Img/ClrMAMEPro/g' /etc/supervisord.conf
