FROM base-ubuntu-caddy-24:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    kde-plasma-desktop \
    konsole \
    dolphin \
    firefox \
    dbus-x11 \
    tigervnc-standalone-server \
    novnc \
    websockify \
    htop \
    sudo \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN usermod -aG sudo runuser

COPY Caddyfile /etc/

RUN echo \
'\n[program:x11]\n\
priority=0\n\
command=/usr/bin/Xtigervnc -desktop "Ubuntu KDE Desktop" -localhost -rfbport 5900 -SecurityTypes None -AlwaysShared -AcceptKeyEvents -AcceptPointerEvents -AcceptSetDesktopSize -SendCutText -AcceptCutText :0\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n\
[program:websockify]\n\
command=/usr/bin/websockify --web /usr/share/novnc 8080 localhost:5900\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n\
\n\
[program:kde]\n\
priority=1\n\
command=/bin/bash -c '"'"'export DISPLAY=:0 && mkdir -p /home/runuser/.config && exec dbus-launch --exit-with-session startplasma-x11'"'"'\n\
environment=DISPLAY=:0,HOME=/home/runuser\n\
autorestart=true\n\
stdout_logfile=/home/runuser/kde.log\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
