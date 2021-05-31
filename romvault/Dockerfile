FROM ubuntu-wine-base:latest

RUN mkdir /app && \
    wget -P /app https://www.romvault.com/download/ROMVault_V3.2.5.zip
WORKDIR /app
RUN unzip ROMVault_V3.2.5.zip && \
    chown -R app:app /app && \
    rm -f ROMVault_V3.2.5.zip
VOLUME /app

RUN echo \
'\nchown app:app /app\n' \
>> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
command=/usr/bin/wine /app/ROMVault3.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/RomVault/g' /etc/supervisord.conf
