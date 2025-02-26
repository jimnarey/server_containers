FROM base-ubuntu-wine-24:latest

WORKDIR /home/runuser

RUN wget https://release.lightburnsoftware.com/LightBurn/Release/LightBurn-v1.7.06/LightBurn-v1.7.06.exe

COPY install.sh comport.reg /home/runuser/
RUN chmod a+x /home/runuser/install.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=x-terminal-emulator -e "/home/runuser/install.sh"\n\
autorestart=false\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /lasercutting

RUN sed -i 's/Ubuntu GUI App Base Img/LightBurn/g' /etc/supervisord.conf
