FROM base-ubuntu-24:latest

ARG WEBDAV_USERNAME
ARG WEBDAV_PASSWORD

RUN apt-get update && apt-get install -y --no-install-recommends apache2

RUN a2enmod dav && \
    a2enmod dav_fs 

RUN mkdir -p /var/www/html/webdav && \
    chown -R www-data:www-data /var/www/html/webdav && \
    chmod -R 755 /var/www/html/webdav

RUN htpasswd -bc /etc/apache2/webdav.password ${WEBDAV_USERNAME} ${WEBDAV_PASSWORD}

RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN sed -i '/<\/VirtualHost>/i\
      <Directory /var/www/html/webdav>\
\n        Options Indexes FollowSymLinks\
\n        AllowOverride None\
\n        Dav On\
\n        AuthType Basic\
\n        AuthName "WebDAV Server"\
\n        AuthUserFile /etc/apache2/webdav.password\
\n        Require valid-user\
\n        </Directory>\
\n' /etc/apache2/sites-available/000-default.conf

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]