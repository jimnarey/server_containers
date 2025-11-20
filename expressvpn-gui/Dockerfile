
FROM base-ubuntu-xfce-24

RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium-browser sudo expect

RUN echo 'runuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

COPY expressvpn-linux-universal-4.1.1.10039.run /home/runuser
RUN chown runuser:runuser /home/runuser/expressvpn-linux-universal-4.1.1.10039.run
RUN chmod +x /home/runuser/expressvpn-linux-universal-4.1.1.10039.run

USER runuser

RUN /home/runuser/expressvpn-linux-universal-4.1.1.10039.run || true

USER root

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN echo \
'\n[program:expressvpn]\n\
command=/opt/expressvpn/bin/expressvpn-daemon\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/var/log/expressvpn.log\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf