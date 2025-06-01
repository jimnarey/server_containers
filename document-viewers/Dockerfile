FROM base-ubuntu-gui-24:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends dolphin


RUN apt-get install -y --no-install-recommends unzip zip p7zip-full p7zip-rar rar unrar tar gzip bzip2 xz-utils lzma lz4 zstd cpio sharutils arj cabextract

RUN apt-get install -y --no-install-recommends qt5ct

RUN apt-get clean
RUN apt-get -y autoremove
RUN rm -rf /var/lib/apt/lists

RUN mkdir /home/runuser/f3d
WORKDIR /home/runuser/f3d
RUN wget https://github.com/f3d-app/f3d/releases/download/v3.0.0/F3D-3.0.0-Linux-x86_64-raytracing.tar.xz
RUN ls -la
RUN tar -xvf F3D-3.0.0-Linux-x86_64-raytracing.tar.xz
RUN ln -s /home/runuser/f3d/F3D-3.0.0-Linux-x86_64-raytracing/bin/f3d /usr/local/bin/f3d

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/bin/dolphin /host_volumes\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN mkdir /host_volumes

RUN sed -i 's/Ubuntu GUI App Base Img/Document Viewers/g' /etc/supervisord.conf
RUN sed -i 's/<maximized>yes<\/maximized>/\n/g' /etc/xdg/openbox/rc.xml

