FROM base-ubuntu-xfce-22:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg flatpak git python3-tk python3-pil python3-pip \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN cd /home/runuser && \
    git clone https://github.com/Voljega/ExoDOSConverter.git && \
    cd ExoDOSConverter && \
    pip3 install -r requirements.txt
  
