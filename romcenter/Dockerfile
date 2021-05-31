FROM ubuntu-wine-base:latest

RUN mkdir /app && \
    wget -P /app https://www.romcenter.com/downloadfile.php?file=romcenter32_4.1.1.7z
WORKDIR /app
RUN 7z x romcenter32_4.1.1.7z && \
    chown -R app:app /app && \
    rm -f romcenter32_4.1.1.7z
VOLUME /app

RUN echo \
'\nchown app:app /app\n' \
>> /usr/local/bin/init_chowns.sh

# RUN echo \
# '\n[program:app]\n\
# priority=1\n\
# environment=DISPLAY=:0,\n\
#             USER=app\n\
# command=/usr/bin/wine /app/ROMVault3.exe\n\
# autorestart=true\n\
# stdout_logfile=/dev/fd/1\n\
# stdout_logfile_maxbytes=0\n\
# redirect_stderr=true\n'\
# >> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/RomCenter/g' /etc/supervisord.conf
