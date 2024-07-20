
FROM base-ubuntu-24

ENV EXPRESS_VPN_ACTIVATION_CODE Code
ENV EXPRESS_VPN_LOCATION smart
ENV EXPRESS_VPN_PREFERRED_PROTOCOL auto
ENV EXPRESS_VPN_LIGHTWAY_CIPHER auto

ARG APP=expressvpn_3.57.1.2-1_amd64.deb

RUN apt-get update && apt-get install -y --no-install-recommends \
    libterm-readkey-perl ca-certificates wget expect iproute2 iputils-ping curl procps libnm0 \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q "https://www.expressvpn.works/clients/linux/${APP}" -O /tmp/${APP} \
    && dpkg -i /tmp/${APP} \
    && rm -rf /tmp/*.deb

COPY entrypoint.sh /tmp/entrypoint.sh
COPY expressvpnActivate.sh /tmp/expressvpnActivate.sh

ENTRYPOINT ["/bin/bash", "/tmp/entrypoint.sh"]
