FROM base-ubuntu:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends  wget \
                                                build-essential \
                                                libreoffice \
                                                imagemagick \
                                                liblog4j1.2-java \
                                                binutils \
                                                zlib1g-dev \
                                                libjpeg-turbo8-dev \
                                                libfreetype6-dev \
                                                libgif-dev \
                                                ant \
                                                curl \
                                                unzip \
                                                sudo \
                                                tesseract-ocr \
                                                tesseract-ocr-eng \
                                                tesseract-ocr-deu && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN wget -O /usr/lib/jvm/jdk-8u281-linux-x64.tar.gz -c --header "Cookie: oraclelicense=accept-securebackup-cookie" https://javadl.oracle.com/webapps/download/GetFile/1.8.0_281-b09/89d678f2be164786b292527658ca1605/linux-i586/jdk-8u281-linux-x64.tar.gz && \
    tar zxvf /usr/lib/jvm/jdk-8u281-linux-x64.tar.gz --directory /usr/lib/jvm && rm /usr/lib/jvm/jdk-8u281-linux-x64.tar.gz && \
    unlink /etc/alternatives/java && ln -s /usr/lib/jvm/jdk1.8.0_281/bin/java /etc/alternatives/java

ENV PATH="$PATH:/usr/lib/jvm/jdk1.8.0_281/bin"
ENV CATALINA_HOME=/usr/local/tomcat
ENV JAVA_HOME=/usr/local/java
ENV OPENJDK_HOME=/usr/lib/jvm/jdk1.8.0_281/
ENV TOMCAT_HOME="$CATALINA_HOME"

RUN ln -s $OPENJDK_HOME $JAVA_HOME && \
    wget -O /usr/local/openkm-tomcat-bundle.zip https://sourceforge.net/projects/openkm/files/6.3.2/openkm-6.3.2-community-tomcat-bundle.zip/download && unzip /usr/local/openkm-tomcat-bundle.zip -d /usr/local/ && rm /usr/local/openkm-tomcat-bundle.zip && ln -s $CATALINA_HOME /opt/openkm && \
    wget -O /tmp/openkm-6.3.10.zip https://sourceforge.net/projects/openkm/files/6.3.10/OpenKM-6.3.10.zip/download && unzip /tmp/openkm-6.3.10.zip -d /tmp/ && mv /tmp/OpenKM.war $TOMCAT_HOME/webapps/ && rm /tmp/openkm-6.3.10.zip /tmp/md5sum.txt && \
    sed -i 's|http://www.springframework.org/schema/security/spring-security-3.1.xsd|http://www.springframework.org/schema/security/spring-security-3.2.xsd|' $TOMCAT_HOME/OpenKM.xml

RUN echo \
'\n[program:app]\n\
priority=1\n\
environment=DISPLAY=:0,\n\
            USER=runuser\n\
command=/usr/local/tomcat/bin/catalina.sh run\n\
autorestart=true\n\
stdout_logfile=/dev/fd/1\n\
stdout_logfile_maxbytes=0\n\
redirect_stderr=true\n'\
>> /etc/supervisord.conf

RUN echo \
'\nchown -R runuser:runuser /usr/local/tomcat\n' \
>> /usr/local/bin/init_chowns.sh
