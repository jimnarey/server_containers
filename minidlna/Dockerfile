FROM base-ubuntu:latest

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends minidlna && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

# RUN cat /etc/minidlna.conf

RUN mkdir /music /video /pictures /home/runuser/db /home/runuser/log

RUN sed -i 's/#db_dir=\/var\/cache\/minidlna/db_dir=\/home\/runuser\/db/g' /etc/minidlna.conf && \
    sed -i 's/#log_dir=\/var\/log/log_dir=\/home\/runuser\/log/g' /etc/minidlna.conf && \
    # sed -i 's/port=8200/port=8080/g' /etc/minidlna.conf && \
    sed -i 's/media_dir=\/var\/lib\/minidlna/media_dir=V,\/video\nmedia_dir=A,\/music\nmedia_dir=P,\/pictures/g' /etc/minidlna.conf

RUN cat /etc/minidlna.conf

# RUN echo \
# '\nchown runuser:runuser /music\n\
# chown runuser:runuser /video\n\
# chown runuser:runuser /pictures\n' \
# >> /usr/local/bin/init_chowns.sh

RUN echo \
'\n[program:app]\n\
priority=1\n\
command=/usr/sbin/minidlnad -S\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf