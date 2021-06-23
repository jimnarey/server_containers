FROM base-ubuntu:latest

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends perl curl build-essential sqlite3 perl-doc libdbi-perl libdbd-sqlite3-perl && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN cpan common::sense && \
    cpan Linux::Inotify2

RUN mkdir -p /opt/idrive
WORKDIR /opt/idrive
RUN wget https://www.idrivedownloads.com/downloads/linux/download-for-linux/LinuxScripts/IDriveForLinux.zip && \
    unzip IDriveForLinux.zip && \
    rm IDriveForLinux.zip && \
    chmod +x IDriveForLinux/scripts/*.pl

ARG IDRIVE_BACKUP_ROOT
ARG IDRIVE_RESTORE_ROOT
ARG IDRIVE_SERVICE_ROOT
ARG IDRIVE_PROFILE_NAME

# This bit of fiddling with usernames is needed so that a container can be started which looks to iDrive as though it's the
# same as the host machine 

RUN userdel runuser && \
    groupadd --gid 1000 $IDRIVE_PROFILE_NAME && \
    useradd --home-dir /home/$IDRIVE_PROFILE_NAME --shell /bin/bash --uid 1000 --gid 1000 $IDRIVE_PROFILE_NAME && \
    mkdir -p /data
VOLUME /home/$IDRIVE_PROFILE_NAME

RUN chown -R fileman:fileman /opt/idrive

RUN sed -i 's/runuser/'$IDRIVE_PROFILE_NAME'/g' /usr/local/bin/start.sh
RUN sed -i 's/runuser/'$IDRIVE_PROFILE_NAME'/g' /usr/local/bin/init_chowns.sh

RUN mkdir -p $IDRIVE_BACKUP_ROOT && \
    mkdir -p $IDRIVE_RESTORE_ROOT && \
    mkdir -p $IDRIVE_SERVICE_ROOT
