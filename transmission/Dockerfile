FROM base-ubuntu:latest

ARG TRANSMISSION_PASSWORD

RUN apt-get update && \
    apt-get install -y --no-install-recommends transmission-common transmission-daemon transmission-cli \
    openvpn openvpn-systemd-resolved && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/transmission-daemon --log-debug --foreground --config-dir /transmission_config\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN mkdir /transmission_config
COPY settings.json /transmission_config
RUN chown -R runuser:runuser /transmission_config

COPY transmission-daemon.conf /etc/init
RUN chown -R runuser:runuser /var/lib/transmission-daemon

RUN sed -i 's/Ubuntu GUI App Base Img/Transmission/g' /etc/supervisord.conf

RUN sed -i "s/PASSWORD/$TRANSMISSION_PASSWORD/g" /transmission_config/settings.json

EXPOSE 9091 51413/tcp 51413/udp

