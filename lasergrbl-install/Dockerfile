FROM base-ubuntu-wine-24:latest

RUN apt install libmpg123-0:i386 && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /home/runuser/lgrbl_dl
WORKDIR /home/runuser/lgrbl_dl
RUN wget https://github.com/arkypita/LaserGRBL/releases/download/v7.11.0/install.exe

COPY comport.reg /home/runuser

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

