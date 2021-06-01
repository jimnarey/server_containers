FROM base-ubuntu-wine:latest

RUN mkdir -p /usr/share/npp
COPY npp.7.9.5.portable.x64.zip /usr/share/npp/npp.zip
WORKDIR /usr/share/npp
RUN unzip npp.zip && \
    cp langs.model.xml langs.xml && \
    cp stylers.model.xml stylers.xml

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=app\n\
# CHANGE APP NAME HERE\n\
command=/usr/bin/wine /usr/share/npp/notepad++.exe\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf
