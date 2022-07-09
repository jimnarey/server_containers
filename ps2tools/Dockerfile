FROM base-ubuntu-wine-alt:latest

COPY init_chowns.sh /usr/local/bin
RUN chmod 744 /usr/local/bin/init_chowns.sh

RUN mkdir -p /home/runuser/tools
RUN mkdir -p /home/runuser/wine/

ENV WINEPREFIX=/home/runuser/wine/
ENV WINEARCH=win64
RUN winecfg

RUN mkdir -p /home/runuser/tools/USBUtil
COPY tools/windows/USBUtil /home/runuser/tools/

COPY tools/iso2opl /usr/bin
RUN chmod +x /usr/bin/iso2opl

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=wine /home/runuser/tools/USBUtil/USBUtil v2.2 rev1.0_English.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir -p /host_media
RUN mkdir -p /host_mnt
