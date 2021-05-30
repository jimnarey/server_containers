# FROM golang:1.16 AS easy-novnc-build
# WORKDIR /src
# RUN go mod init build && \
#     go get github.com/geek1011/easy-novnc@v1.1.0 && \
#     go build -o /bin/easy-novnc github.com/geek1011/easy-novnc

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
    apt-get install -y --no-install-recommends supervisor gosu nano wget openssh-client rsync ca-certificates xdg-utils htop tar xzip gzip bzip2 zip unzip && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists


# RUN apt-get update -y && \
#     apt-get install -y --no-install-recommends openbox tigervnc-standalone-server lxterminal && \
#     apt-get clean && \
#     apt-get autoremove && \
#     rm -rf /var/lib/apt/lists

# RUN mkdir -p /usr/share/desktop-directories

# COPY --from=easy-novnc-build /bin/easy-novnc /usr/local/bin/
# COPY menu.xml /etc/xdg/openbox/

#
# Copy an amended rc.xml to reduce number of desktops to 1 and
# maximising all apps on start
#
# COPY rc.xml /etc/xdg/openbox/rc.xml

#
# The amended rc.xml file above points to the right menu.xml path but
# in case this is not used, the command below will achieve the same thing.
#
# RUN ln -s /etc/xdg/openbox/menu.xml /var/lib/openbox/debian-menu.xml
#
COPY supervisord.conf /etc/

COPY --from=caddy-build /bin/caddy /usr/local/bin/
COPY Caddyfile /etc/
ENV CADDY_USER=admin
# Hash for 'password'
ENV CADDY_HASH=JDJhJDEwJE84L1BrOFdSNmxxdUgveGFMRGJieE9kRXVERm1DTDJTMXpmQWdoS1ZNSFNNZHdTb3oxU0k2

COPY start.sh /usr/local/bin
COPY init_chowns.sh /usr/local/bin
RUN chmod 744 /usr/local/bin/start.sh
RUN chmod 744 /usr/local/bin/init_chowns.sh

EXPOSE 8081

RUN groupadd --gid 1000 app && \
    useradd --home-dir /data --shell /bin/bash --uid 1000 --gid 1000 app && \
    mkdir -p /data
VOLUME /data

# CMD ["sh", "-c", "chown app:app /data /dev/stdout && exec gosu app supervisord"]

CMD ["/usr/local/bin/start.sh"]
