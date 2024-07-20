FROM base-ubuntu-caddy-24:latest


ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends openbox novnc websockify lxterminal htop \
    tigervnc-standalone-server && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists
    
COPY Caddyfile /etc/

COPY menu.xml /etc/xdg/openbox/

COPY rc.xml /etc/xdg/openbox/rc.xml

RUN echo \
'\n[program:x11]\n\
priority=0\n\
# CHANGE APP TITLE HERE\n\
command=/usr/bin/Xtigervnc -desktop "Ubuntu GUI App Base Img" -localhost -rfbport 5900 -SecurityTypes None -AlwaysShared -AcceptKeyEvents -AcceptPointerEvents -AcceptSetDesktopSize -SendCutText -AcceptCutText :0\n\
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
[program:openbox]\n\
priority=1\n\
command=/usr/bin/openbox\n\
environment=DISPLAY=:0\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf


