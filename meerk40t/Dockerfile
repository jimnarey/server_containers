FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends fuse && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir /app
WORKDIR /app

RUN wget https://github.com/meerk40t/meerk40t/releases/download/weekly-26/MeerK40t-linux-26.AppImage && \
    chmod a+x MeerK40t-linux-26.AppImage 

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/app/MeerK40t-linux-26.AppImage\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN sed -i 's/Ubuntu GUI App Base Img/MeerK40t/g' /etc/supervisord.conf


