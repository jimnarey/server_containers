FROM base-ubuntu-wine-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends nemo && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

# The application is extracted to a volume because it stores data in the same dir
RUN mkdir -p /app/nkit /app/wbm /app/gcit
COPY NKit_v1.4.zip WiiBackupManager_Build78.zip gcit_Win32_Build7.zip /app
WORKDIR /app
RUN unzip NKit_v1.4.zip -d /app/nkit
# unzip works on this file but exits with a 1 due to a warning
# about the zip file using backslashes internally
RUN unzip WiiBackupManager_Build78.zip -d /app/wbm  || [ $? -eq 1 ]
RUN unzip gcit_Win32_Build7.zip -d /app/gcit
RUN	rm -f NKit_v1.4.zip WiiBackupManager_Build78.zip gcit_Win32_Build7.zip
RUN  chown -R runuser:runuser /app
VOLUME /app

RUN echo \
'\nchown -R runuser:runuser /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:nkit]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/nkit/NKitProcessingApp.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n[program:wbm]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/wbm/WiiBackupManager_Win64.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n[program:gcit]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/gcit/gcit.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
[program:nemo]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=nemo\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_mnt && \
    mkdir /host_media

RUN sed -i 's/Ubuntu GUI App Base Img/Nkit/g' /etc/supervisord.conf
