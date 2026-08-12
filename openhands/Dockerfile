FROM ghcr.io/openhands/agent-canvas:1.7.0

USER root

# The upstream image reserves 1000:1000 for a legacy "pn" account and runs
# OpenHands as 10001:10001. Reassign the real account so a numeric Compose user
# still has a meaningful passwd/group identity and the documented home.
RUN userdel pn && \
    groupmod --gid 1000 openhands && \
    usermod --uid 1000 --gid 1000 openhands && \
    chown -R 1000:1000 /home/openhands

USER openhands
