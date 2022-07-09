FROM base-ubuntu-18


RUN apt-get update && \
    apt-get install -y --no-install-recommends python python-dev expect device-tree-compiler \
    python python-kerberos repo python-dev expect device-tree-compiler build-essential && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

COPY start.sh /usr/local/bin
COPY init_chowns.sh /usr/local/bin
RUN chmod 744 /usr/local/bin/start.sh
RUN chmod 744 /usr/local/bin/init_chowns.sh

RUN mkdir /buildroot_root

CMD ["/bin/bash"]
