FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends libusb-1.0-0 libpulse-mainloop-glib0 fuse && \
    apt-get install -y --reinstall libxcb-xinerama0 && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir /lasercutting

WORKDIR /home/runuser
RUN wget --no-check-certificate -nv https://github.com/LightBurnSoftware/deployment/releases/download/1.6.03/LightBurn-Linux64-v1.6.03.AppImage && \
    chmod a+x /home/runuser/LightBurn-Linux64-v1.6.03.AppImage && \
    /home/runuser/LightBurn-Linux64-v1.6.03.AppImage --appimage-extract && \
    chown -R runuser:runuser /home/runuser 

RUN ls -la /home/runuser

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/home/runuser/squashfs-root/AppRun\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /lightburn

RUN sed -i 's/Ubuntu GUI App Base Img/LightBurn/g' /etc/supervisord.conf
