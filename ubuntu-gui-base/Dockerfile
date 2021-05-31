# FROM golang:1.16 AS easy-novnc-build
# WORKDIR /src
# RUN go mod init build && \
#     go get github.com/geek1011/easy-novnc@v1.1.0 && \
#     go build -o /bin/easy-novnc github.com/geek1011/easy-novnc

FROM ubuntu-headless-base:latest

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends openbox tigervnc-standalone-server lxterminal && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /usr/share/desktop-directories

# COPY --from=easy-novnc-build /bin/easy-novnc /usr/local/bin/
COPY --from=build-easy-novnc /bin/easy-novnc /usr/local/bin/
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