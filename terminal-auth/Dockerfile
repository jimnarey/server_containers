FROM golang:1.16 AS easy-novnc-build
WORKDIR /src
RUN go mod init build && \
    go get github.com/geek1011/easy-novnc@v1.1.0 && \
    go build -o /bin/easy-novnc github.com/geek1011/easy-novnc

FROM golang:1.14 AS caddy-build
WORKDIR /src
RUN echo 'module caddy' > go.mod && \
    echo 'require github.com/caddyserver/caddy/v2 v2.1.1' >> go.mod && \
    echo 'require github.com/mholt/caddy-webdav v0.0.0-20200523051447-bc5d19941ac3' >> go.mod
RUN echo 'package main' > caddy.go && \
    echo 'import caddycmd "github.com/caddyserver/caddy/v2/cmd"' >> caddy.go && \
    echo 'import _ "github.com/caddyserver/caddy/v2/modules/standard"' >> caddy.go && \
    echo 'import _ "github.com/mholt/caddy-webdav"' >> caddy.go && \
    echo 'func main() { caddycmd.Main() }' >> caddy.go
RUN go get
RUN go build -o /bin/caddy .


FROM ubuntu:20.04

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends openbox tigervnc-standalone-server supervisor gosu && \
    rm -rf /var/lib/apt/lists && \
    mkdir -p /usr/share/desktop-directories

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends lxterminal nano wget openssh-client rsync ca-certificates xdg-utils htop tar xzip gzip bzip2 zip unzip && \
    rm -rf /var/lib/apt/lists

#
# CHANGE THUNDERBIRD TO DESIRED APP
#
#If you are containerizing a different application, you can replace 
#these commands with the ones required to install your specific app. 
#Some applications will require a bit more work to run inside Docker. 
#For example, if you are installing an app that uses Chrome, Chromium, 
#or QtWebEngine, you’ll need to use the command line argument 
#--no-sandbox because it won’t be supported within Docker.
#
# RUN apt-get update -y && \
#     apt-get install -y --no-install-recommends playonlinux && \
#     rm -rf /var/lib/apt/lists

COPY --from=easy-novnc-build /bin/easy-novnc /usr/local/bin/
COPY menu.xml /etc/xdg/openbox/
COPY rc.xml /etc/xdg/openbox/rc.xml
# RUN ln -s /etc/xdg/openbox/menu.xml /var/lib/openbox/debian-menu.xml
COPY supervisord.conf /etc/

COPY --from=caddy-build /bin/caddy /usr/local/bin/
COPY Caddyfile /etc/

EXPOSE 8081

RUN groupadd --gid 1000 app && \
    useradd --home-dir /data --shell /bin/bash --uid 1000 --gid 1000 app && \
    mkdir -p /data
VOLUME /data

CMD ["sh", "-c", "chown app:app /data /dev/stdout && exec gosu app supervisord"]
