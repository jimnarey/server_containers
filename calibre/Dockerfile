FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends xz-utils libnss3 libxcb-xinerama0 libxcb-cursor0 \
    libxcb-randr0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxkbcommon-x11-0 \
    dbus fcitx-rime fonts-wqy-microhei jq libqpdf29t64 libopengl0 python3 python3-xdg ttf-wqy-zenhei && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN wget --no-check-certificate -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin

RUN mkdir /library
RUN mkdir /source

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/calibre\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

COPY Caddyfile /etc/

RUN sed -i 's/Ubuntu GUI App Base Img/Calibre/g' /etc/supervisord.conf
