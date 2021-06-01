FROM ubuntu:20.04

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends supervisor gosu nano wget openssh-client rsync ca-certificates xdg-utils tar xzip gzip bzip2 zip unzip p7zip-full && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY supervisord.conf /etc/

COPY start.sh /usr/local/bin
COPY init_chowns.sh /usr/local/bin
RUN chmod 744 /usr/local/bin/start.sh
RUN chmod 744 /usr/local/bin/init_chowns.sh

RUN groupadd --gid 1000 app && \
    useradd --home-dir /data --shell /bin/bash --uid 1000 --gid 1000 app && \
    mkdir -p /data
VOLUME /data

CMD ["/usr/local/bin/start.sh"]
