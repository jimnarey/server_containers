FROM ubuntu-wine-base:latest

RUN mkdir /app && \
    wget -P /app https://www.romvault.com/download/ROMVault_V3.2.5.zip
WORKDIR /app
RUN unzip ROMVault_V3.2.5.zip && \
    chown -R app:app /app && \
    rm -f ROMVault_V3.2.5.zip
VOLUME /app

# RUN apt-get update && \ 
#     apt-get install -y --install-recommends mono-complete && \
#     rm -rf /var/lib/apt/lists

# ENV WINEPREFIX /data/prefix32
# ENV WINEARCH win32

# COPY ndp472-kb4054530-x86-x64-allos-enu.exe /usr/share/wine/mono
# RUN wine /usr/share/wine/mono/ndp472-kb4054530-x86-x64-allos-enu.exe /q /norestart

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
