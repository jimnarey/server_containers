FROM base-ubuntu-24:latest

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends samba samba-vfs-modules && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/*

COPY supervisord.conf /etc/
COPY start.sh /usr/local/bin/start.sh
RUN chmod 744 /usr/local/bin/start.sh

EXPOSE 445/tcp 139/tcp 137/udp 138/udp

CMD ["/usr/local/bin/start.sh"]
