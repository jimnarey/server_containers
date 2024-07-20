FROM base-ubuntu-wine-24:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir /lasercutting

RUN export WINEARCH=win32

RUN apt-get update && \
    apt-get -y install playonlinux && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir /custom_buttons
WORKDIR /custom_buttons
RUN wget https://lasergrbl.com/wp-content/uploads/2020/07/CustomButtons.gz
RUN chown -R runuser:runuser /custom_buttons

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=playonlinux\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN sed -i 's/Ubuntu GUI App Base Img/LaserGRBL/g' /etc/supervisord.conf

