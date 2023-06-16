FROM base-ubuntu-gui:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends libusb-1.0-0 libpulse-mainloop-glib0 && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir /lightburn_install
WORKDIR /lightburn_install
    
RUN wget --no-check-certificate -nv https://github.com/LightBurnSoftware/deployment/releases/download/1.2.04/LightBurn-Linux64-v1.2.04.7z && \
    7z x LightBurn-Linux64-v1.2.04.7z && \
    mv LightBurn /opt 

WORKDIR /home/runuser
RUN rm -rf /lightburn_install

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/opt/LightBurn/LightBurn\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /lightburn

RUN sed -i 's/Ubuntu GUI App Base Img/LightBurn/g' /etc/supervisord.conf

