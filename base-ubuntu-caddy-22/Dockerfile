FROM base-ubuntu-22:latest

RUN mkdir -p /home/runuser/caddy_dl
WORKDIR /home/runuser/caddy_dl
RUN wget https://github.com/caddyserver/caddy/releases/download/v2.8.2/caddy_2.8.2_linux_amd64.tar.gz
RUN tar -xvf caddy_2.8.2_linux_amd64.tar.gz && \
    cp caddy /usr/local/bin

WORKDIR /home/runuser
RUN rm -rf caddy_dl

COPY Caddyfile /etc/
ENV CADDY_USER=admin
# Hash for 'password'
ENV CADDY_HASH=JDJhJDEwJE84L1BrOFdSNmxxdUgveGFMRGJieE9kRXVERm1DTDJTMXpmQWdoS1ZNSFNNZHdTb3oxU0k2

EXPOSE 8081

RUN echo \
'\n[program:caddy]\n\
priority=1\n\
command=/usr/local/bin/caddy run --adapter caddyfile --config /etc/Caddyfile\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n' \
>> /etc/supervisord.conf

