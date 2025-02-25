FROM base-ubuntu-wine-24:latest

ARG DEBIAN_FRONTEND=noninteractive

ENV WINEARCH=win32

RUN apt-get update && \
    apt-get install --no-install-recommends -y libmpg123-0:i386 libgl1:i386 winetricks 

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

WORKDIR /home/runuser
RUN wget https://github.com/arkypita/LaserGRBL/releases/download/v7.14.0/install.exe

RUN mkdir /custom_buttons
WORKDIR /custom_buttons
RUN wget https://lasergrbl.com/wp-content/uploads/2020/07/CustomButtons.gz
RUN chown -R runuser:runuser /custom_buttons

RUN mkdir /lasercutting

COPY install.sh /home/runuser
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
