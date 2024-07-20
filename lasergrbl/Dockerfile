FROM base-ubuntu-wine-24:latest

RUN mkdir /lasercutting

RUN export WINEARCH=win32

RUN apt install libmpg123-0:i386 && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists


RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=wine "/home/runuser/.wine/drive_c/Program Files (x86)/LaserGRBL/LaserGRBL.exe"\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/LaserGRBL/g' /etc/supervisord.conf

