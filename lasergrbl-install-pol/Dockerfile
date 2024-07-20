FROM base-ubuntu-wine-24:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get -y install playonlinux && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

WORKDIR /home/runuser
RUN wget https://github.com/arkypita/LaserGRBL/releases/download/v7.11.0/install.exe

COPY install.sh /home/runuser
COPY POL_LaserGRBL_setup.sh /home/runuser
RUN chmod a+x /home/runuser/*.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=x-terminal-emulator\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/LaserGRBL Install/g' /etc/supervisord.conf

