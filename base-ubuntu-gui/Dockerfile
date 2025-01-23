FROM base-ubuntu-caddy:latest

# RUN apt-get update -y && \
#     apt-get install -y --no-install-recommends openbox tigervnc-standalone-server lxterminal htop && \
#     apt-get clean && \
#     apt-get autoremove && \
#     rm -rf /var/lib/apt/lists

# RUN mkdir -p /usr/share/desktop-directories

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends openbox novnc websockify lxterminal htop \
    tigervnc-standalone-server && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists
    
COPY Caddyfile /etc/

# COPY --from=build-easy-novnc /bin/easy-novnc /usr/local/bin/
COPY menu.xml /etc/xdg/openbox/

#
# Copy an amended rc.xml to reduce number of desktops to 1 and
# maximising all apps on start
#
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
[program:easy-novnc]\n\
priority=0\n\
command=/usr/local/bin/easy-novnc --addr :8080 --host localhost --port 5900 --no-url-password --novnc-params "resize=remote"\n\
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
