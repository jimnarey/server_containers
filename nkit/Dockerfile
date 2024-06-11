FROM base-ubuntu-wine:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends nemo && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

# The application is extracted to a volume because it stores data in the same dir
RUN mkdir /app
COPY NKit_v1.4.zip /app
WORKDIR /app
RUN unzip NKit_v1.4.zip && \
    chown -R runuser:runuser /app && \
    rm -f NKit_v1.4.zip
VOLUME /app

RUN echo \
'\nchown -R runuser:runuser /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/wine /app/NKitProcessingApp.exe\n\
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
