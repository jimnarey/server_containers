FROM base-ubuntu:latest

WORKDIR /home/runuser
RUN wget https://mega.nz/linux/repo/xUbuntu_20.04/amd64/megacmd_1.5.0-10.1_amd64.deb && \
    apt-get update -y && \
    apt-get install -y ./megacmd_1.5.0-10.1_amd64.deb dbus && \
    rm ./megacmd_1.5.0-10.1_amd64.deb && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN dbus-uuidgen > /etc/machine-id

ARG MEGANZ_SYNC_A

ARG MEGANZ_SYNC_B

RUN mkdir -p $MEGANZ_SYNC_A

RUN mkdir -p $MEGANZ_SYNC_B

RUN echo \
'\n[program:mega-cmd-server]\n\
priority=1\n\
command=/usr/bin/mega-cmd-server\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n' \
>> /etc/supervisord.conf
