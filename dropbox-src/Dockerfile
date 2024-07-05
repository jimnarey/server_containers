FROM base-ubuntu-22:latest

WORKDIR /home/runuser

RUN wget -O dropbox.tar.gz "https://www.dropbox.com/download?plat=lnx.x86_64" && \
   tar -xzf dropbox.tar.gz && \
   wget -O dropbox.py https://www.dropbox.com/download?dl=packages/dropbox.py && \
   chmod +x dropbox.py

RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 libglapi-mesa libxext-dev libxdamage-dev libxcb-glx0-dev libxcb-dri2-0-dev libxcb-dri3-dev \
    libxcb-present-dev libxshmfence-dev libxxf86vm-dev libqt5x11extras5
    
RUN apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists

RUN mkdir -p /home/runuser/Dropbox

RUN ln -s /home/runuser/dropbox.py /usr/local/bin/dropbox

WORKDIR /home/runuser/Dropbox
