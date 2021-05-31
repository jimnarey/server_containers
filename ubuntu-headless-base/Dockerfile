# FROM golang:1.14 AS caddy-build
# WORKDIR /src
# RUN echo 'module caddy' > go.mod && \
#     echo 'require github.com/caddyserver/caddy/v2 v2.1.1' >> go.mod && \
#     echo 'require github.com/mholt/caddy-webdav v0.0.0-20200523051447-bc5d19941ac3' >> go.mod
# RUN echo 'package main' > caddy.go && \
#     echo 'import caddycmd "github.com/caddyserver/caddy/v2/cmd"' >> caddy.go && \
#     echo 'import _ "github.com/caddyserver/caddy/v2/modules/standard"' >> caddy.go && \
#     echo 'import _ "github.com/mholt/caddy-webdav"' >> caddy.go && \
#     echo 'func main() { caddycmd.Main() }' >> caddy.go
# RUN go get
# RUN go build -o /bin/caddy .


FROM ubuntu:20.04

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends supervisor gosu nano wget openssh-client rsync ca-certificates xdg-utils htop tar xzip gzip bzip2 zip unzip p7zip-full && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

COPY supervisord.conf /etc/

# COPY --from=caddy-build /bin/caddy /usr/local/bin/
COPY --from=build-caddy /bin/caddy /usr/local/bin/
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

CMD ["/usr/local/bin/start.sh"]
