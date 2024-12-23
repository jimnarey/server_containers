FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg wget build-essential \
    libusb-1.0-0-dev libudev-dev git npm

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN npm install -g npm@8.19.4

RUN npm install -g node@12.22.12

RUN git clone https://github.com/LaserWeb/LaserWeb4.git /LaserWeb4

WORKDIR /LaserWeb4

RUN git submodule init && git submodule update

RUN npm install

RUN npm run bundle-dev

RUN git clone https://github.com/LaserWeb/lw.comm-server.git /lw.comm-server

WORKDIR /lw.comm-server

RUN npm install serialport --unsafe-perm

RUN npm install

RUN npm run update_frontend

RUN echo \
'\n[program:lwserver]\n\
priority=1\n\
environment=USER=root\n\
command=bash -c "exec node /lw.comm-server/server.js"\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN install -d -m 0755 /etc/apt/keyrings

RUN wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- | tee /etc/apt/keyrings/packages.mozilla.org.asc > /dev/null

RUN echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" | tee -a /etc/apt/sources.list.d/mozilla.list > /dev/null

RUN echo \
'Package: *\n\
Pin: origin packages.mozilla.org\n\
Pin-Priority: 1000\n\n\
Package: firefox*\n\
Pin: release o=Ubuntu\n\
Pin-Priority: -1\n' \
>> /etc/apt/preferences.d/mozilla

RUN apt-get update && \
    apt-get install -y --no-install-recommends firefox

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN echo \
'\n[program:LaserWeb]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=firefox -kiosk 127.0.0.1:8000\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf