FROM base-ubuntu-22:latest

WORKDIR /home/runuser

RUN wget https://www.dropbox.com/download?dl=packages/ubuntu/dropbox_2020.03.04_amd64.deb -O dropbox_2020.03.04_amd64.deb

RUN apt-get update
RUN apt-get install -y ./dropbox_2020.03.04_amd64.deb
    
RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /home/runuser/Dropbox

WORKDIR /home/runuser/Dropbox
