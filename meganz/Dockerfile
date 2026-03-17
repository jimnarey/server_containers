# To get this up and running, first bring it up with a bash prompt
# and login to Mega using rclone. Credentials are then saved in
# home volume

FROM base-ubuntu-24:latest

ARG MEGACMD_PKG=megacmd-xUbuntu_22.04_amd64.deb
ARG RCLONE_VERSION=1.63.1

WORKDIR /home/runuser

RUN wget https://mega.nz/linux/repo/xUbuntu_22.04/amd64/${MEGACMD_PKG}

RUN apt-get update -y && \
    apt-get install -y ./${MEGACMD_PKG} dbus curl unzip ca-certificates && \
    rm ./${MEGACMD_PKG}

RUN wget -q https://downloads.rclone.org/v${RCLONE_VERSION}/rclone-v${RCLONE_VERSION}-linux-amd64.zip && \
    unzip rclone-v${RCLONE_VERSION}-linux-amd64.zip && \
    cp rclone-v${RCLONE_VERSION}-linux-amd64/rclone /usr/bin/ && \
    chown root:root /usr/bin/rclone && \
    chmod 0755 /usr/bin/rclone && \
    rm -rf rclone-v${RCLONE_VERSION}-linux-amd64*

RUN apt-get install -y python3-watchdog

COPY fs_watch.py /usr/local/bin/
RUN chmod +x /usr/local/bin/fs_watch.py

RUN dbus-uuidgen > /etc/machine-id

RUN mkdir /meganz_local

RUN echo \
'\n[program:mega-cmd-server]\n\
priority=1\n\
command=/usr/bin/mega-cmd-server\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n' \
>> /etc/supervisord.conf

RUN echo \
'\n[program:fs-watch]\n\
priority=10\n\
command=/usr/local/bin/fs_watch.py\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n' \
>> /etc/supervisord.conf

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists