FROM ubuntu:18.04


RUN apt-get update && \
    apt-get install -y --no-install-recommends gosu nano wget openssh-client rsync \
    ca-certificates xdg-utils tar xzip gzip bzip2 zip unzip p7zip-full && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


RUN groupadd --gid 1000 runuser && \
    useradd --home-dir /home/runuser --shell /bin/bash --uid 1000 --gid 1000 runuser && \
    mkdir -p /data
VOLUME /home/runuser

CMD ["/usr/local/bin/start.sh"]