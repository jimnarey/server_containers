# ExpressVPN in a container

Adapted from: https://github.com/polkaned/dockerfiles

## Start the container

    docker run \
      --env=EXPRESS_VPN_ACTIVATION_CODE={% your-activation-code %} \
      --env=EXPRESS_VPN_SERVER={% LOCATION/ALIAS/COUNTRY %} \
      --env=EXPRESS_VPN_PREFERRED_PROTOCOL={% protocol %} \
      --env=EXPRESS_VPN_LIGHTWAY_CIPHER={% lightway-cipher %} \
      --cap-add=NET_ADMIN \
      --device=/dev/net/tun \
      --privileged \
      --detach=true \
      --tty=true \
      --name=expressvpn \
      polkaned/expressvpn \
      /bin/bash


## Docker Compose
Other containers can use the network of the expressvpn container by declaring the entry `network_mode: service:expressvpn`.
In this case all traffic is routed via the vpn container. To reach the other containers locally the port forwarding must be done in the vpn container (the network mode service does not allow a port configuration)

```
  version: "3.8"

  services:

    expressvpn:
      container_name: expressvpn-c
      build: ./expressvpn
      env_file:
            - env.sh
      cap_add:
        - NET_ADMIN
      devices: 
        - /dev/net/tun
      stdin_open: true
      tty: true
      command: /bin/bash
      privileged: true
      restart: unless-stopped
      ports:
        - 9092:9091

    transmission:
      image: transmission
      container_name: transmission-vpn-c
      env_file:
        - env.sh
      network_mode: service:expressvpn
      depends_on:
        - expressvpn
      volumes:
        - transmission-vpn-home:/home/runuser

  volumes:
    transmission-vpn-home: {}
```

## Configuration Reference

### ACTIVATION_CODE
A mandatory string containing your ExpressVPN activation code.

`ACTIVATION_CODE=ABCD1EFGH2IJKL3MNOP4QRS`

### SERVER
A optional string containing the ExpressVPN server LOCATION/ALIAS/COUNTRY. Connect to smart location if it is not set.

`SERVER=ukbe`

### PREFERRED_PROTOCOL
A optional string containing the ExpressVPN protocol. Can be auto, udp, tcp ,lightway_udp, lightway_tcp. Use auto if it is not set.

`PREFERRED_PROTOCOL=lightway_udp`

### LIGHTWAY_CIPHER
A optional string containing the ExpressVPN lightway cipher. Can be auto, aes, chacha20. Use auto if it is not set.

`LIGHTWAY_CIPHER=chacha20`
