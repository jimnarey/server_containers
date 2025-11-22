FROM base-ubuntu-caddy-24:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    xfce4 \
    xfce4-goodies \
    xfce4-terminal \
    thunar \
    firefox \
    dbus-x11 \
    tigervnc-standalone-server \
    novnc \
    websockify \
    htop \
    sudo \
    adwaita-icon-theme \
    elementary-xfce-icon-theme \
    tango-icon-theme \
    gnome-icon-theme \
    hicolor-icon-theme \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN usermod -aG sudo runuser

COPY Caddyfile /etc/

RUN echo \
'\n[program:x11]\n\
priority=0\n\
user=runuser\n\
environment=HOME=/home/runuser\n\
command=/usr/bin/Xtigervnc -desktop "Ubuntu XFCE Desktop" -localhost -rfbport 5900 -SecurityTypes None -AlwaysShared -AcceptKeyEvents -AcceptPointerEvents -AcceptSetDesktopSize -SendCutText -AcceptCutText :0\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n\
[program:websockify]\n\
user=runuser\n\
environment=HOME=/home/runuser\n\
command=/usr/bin/websockify --web /usr/share/novnc 8080 localhost:5900\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n\
[program:xfce]\n\
user=runuser\n\
environment=HOME=/home/runuser\n\
priority=1\n\
command=/bin/bash -c '"'"'export DISPLAY=:0 && exec dbus-launch --exit-with-session startxfce4'"'"'\n\
environment=DISPLAY=:0\n\
autorestart=true\n\
stdout_logfile=/home/runuser/xfce.log\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

ENV DISPLAY=:0
